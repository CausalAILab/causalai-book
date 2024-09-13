from __future__ import annotations  # postponed evaluation of annotations

from abc import ABC, abstractmethod
from heapq import heappush, heappushpop, heapreplace
from typing import Callable, Dict, Hashable, Mapping

import torch as T
import torch.multiprocessing as mp
import torch.nn as nn
from tqdm import tqdm

from .distribution import Distribution


def worker_function(i: int, f: Callable, q: mp.Queue, *args):
    q.put(f(*args))


class SCM(nn.Module):
    def __init__(
        self, f: Mapping[Hashable, Callable], pu: Distribution, device: T.Device = None
    ):
        """
        :param f: A dictionary mapping observed variable names to functions.
        :type f: dict
        :param pu: The distribution over exogenous variables.
        :type pu: class:`scm.distribution.Distribution`
        """
        super().__init__()
        self.f = f
        self.pu = pu
        self.v = list(f)
        self.u = list(pu)
        self.device_param = nn.Parameter(T.empty(0))

        if device:
            self.device_param = self.device_param.to(device)

    def __iter__(self):
        return iter(self.v)

    def _process(self):
        while True:
            f, v, u = iq.get()

        return self.f[k](*args)

    def sample(
        self,
        n=None,
        u=None,
        interventions={},
        select=None,
        return_u=False,
        n_jobs=None,
        n_gpus=None,
        n_threads_per_gpu=None,
        progress_bar=False,
        cache_size=700,
    ) -> Dict[Hashable, T.Tensor]:
        """
        :param n: The number of samples to draw, default 1.
        :type n: int
        :param u: A tensor containing unobserved values of u.
                  Cannot be specified when `n` is specified.
        :type u: class:`torch.Tensor`, optional
        :param n_jobs: The number of threads to use in parallelizing
                       interventional sampling, default None - all cores.
        :type n_jobs: int
        """
        assert (n is None) != (u is None)

        if n is not None:
            u = self.pu.sample(n)
        else:
            n = len(next(iter(u.values())))
        interventions = {None: None} | dict(interventions)

        # we assume that u's in intervened worlds do not collide
        # furthermore, we assume they are independent from existing u's
        ut = {}
        scms = {}
        for subscript, intervention in tqdm(
            interventions.items(),
            disable=not progress_bar,
            desc="sample us",
            leave=False,
        ):
            scms[subscript] = (
                self.do(intervention) if intervention is not None else self
            )
            ut.update(scms[subscript].pu.sample(n, exclude=ut))
        ut.update(u)
        ut = {k: v.to(self.device_param.device) for k, v in ut.items()}

        v = {}

        # use an amortized max-heap and min-heap to track which tensors to save
        saved = {}  # cached signature outcomes on cpu/gpu
        hits = {}  # to track frequency of signature usage
        heap_contents = set()
        gpu_heap = []  # min heap: top cache_size signatures for gpu storage
        cpu_heap = []  # max heap: all other signatures

        for subscript, scm in tqdm(
            scms.items(),
            desc="sample vs",
            disable=not progress_bar,
            leave=False,
        ):
            vt = {}
            signature = ()
            diff = 0
            # assert all(v.device == self.device_param.device for k, v in ut.items()), {
            #     k: v.device for k, v in ut.items()
            # }
            for vi in scm.v:
                signature += (hash(scm.f[vi]),)
                diff += hash(scm.f[vi]) != hash(self.f[vi])

                # compute function
                if signature not in saved:
                    try:
                        saved[signature] = scm.f[vi](vt, ut)
                    except Exception:
                        print("Error processing", scm.v)
                        print({k: (v.device, v.shape) for k, v in ut.items()})
                        print({k: (v.device, v.shape) for k, v in vt.items()})
                        raise

                if vi not in vt:
                    if self.device_param.device != saved[signature].device:
                        vt[vi] = saved[signature].to(self.device_param.device)
                    else:
                        vt[vi] = saved[signature]

                if diff > 0:
                    del saved[signature]

            vt = {
                vi if subscript is None else (vi, subscript): val
                for vi, val in vt.items()
            }
            v.update(
                {
                    k: v.clone().cpu()
                    for k, v in vt.items()
                    if select is None or select(k)
                }
            )
            del vt
            T.cuda.empty_cache()

        v = {k: t.to(self.device_param.device) for k, t in v.items()}
        return (v, u) if return_u else v

    def forward(self, n=None, u=None) -> Dict[Hashable, T.Tensor]:
        return self.sample(n=n, u=u)

    def do(self, x: Intervention) -> SCM:
        if isinstance(x, dict):
            x = AtomicIntervention(x)
        return x(self).to(self.device_param.device)


class Intervention(ABC):
    @abstractmethod
    def __call__(self, m: SCM) -> SCM:
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def __eq__(self, other):
        return hash(self) == hash(other)


class NullIntervention(Intervention):
    def __call__(self, m: SCM) -> SCM:
        return m

    def __hash__(self):
        return hash(type(self).__name__)


class AtomicIntervention(Intervention):
    def __init__(self, x: dict):
        super().__init__()
        self.x = {z: x[z] if callable(x[z]) else lambda v, u: x[z] for z in x}

    def __call__(self, m: SCM) -> SCM:
        return SCM(f={z: self.x.get(z, fi) for z, fi in m.f.items()}, pu=m.pu)

    def __hash__(self):
        return hash(type(self).__name__ + ":" + tuple(sorted(self.x.items())))
