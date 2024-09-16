from __future__ import annotations  # postponed evaluation of annotations

import itertools
from abc import ABC, abstractmethod
from typing import Callable, Dict, Hashable, Mapping, Union

import pandas as pd
import torch as T
import torch.multiprocessing as mp
import torch.nn as nn
from tqdm import tqdm


class SCM(nn.Module):
    def __init__(
        self, f: Mapping[Hashable, Callable], pu: Distribution, device: T.Device = None
    ):
        """
        :param f: A dictionary mapping observed variable names to functions.
        :type f: dict
        :param pu: The distribution over exogenous variables.
        :type pu: class:`scm.distribution.Distribution`
        :param device: The device on which to store the SCM.
        :type device: class:`torch.Device`, optional
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

    def sample(
        self,
        n=None,
        u=None,
        interventions={},
        select=None,
        return_u=False,
        progress_bar=False,
    ) -> Dict[Hashable, T.Tensor]:
        """
        :param n: The number of samples to draw, default 1.
        :type n: int
        :param u: A tensor containing unobserved values of u.
                  Cannot be specified when `n` is specified.
        :type u: class:`torch.Tensor`, optional
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

        saved = {}  # cached signature outcomes on cpu/gpu

        for subscript, scm in tqdm(
            scms.items(),
            desc="sample vs",
            disable=not progress_bar,
            leave=False,
        ):
            # a variable's signature is a tuple of hashes of the functions topologically prior to it
            signature = ()
            vt = {}
            diff = 0
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


class Distribution(nn.Module):
    def __init__(self, u):
        super().__init__()
        self.u = list(u)
        self.device_param = nn.Parameter(T.empty(0))

    def __iter__(self):
        return iter(self.u)

    def sample(self, n=1, exclude=set()):
        raise NotImplementedError()

    def forward(self, n=1):
        raise self.sample(n=n)


class JointDistribution(Distribution):
    def __init__(self, *distributions):
        us = set()
        for distribution in distributions:
            assert not us.intersection(distribution)
            us.update(distribution)

        super().__init__([u for distribution in distributions for u in distribution])
        self.distributions = nn.ModuleList(
            sum(
                (
                    list(d.distributions) if isinstance(d, JointDistribution) else [d]
                    for d in distributions
                ),
                [],
            ),
        )

    def sample(self, n=1, exclude=set()):
        if not (set(self.u) - set(exclude)):
            return {}
        return {
            k: v
            for distribution in self.distributions
            for k, v in distribution.sample(n, exclude=exclude).items()
        }


class NormalDistribution(Distribution):
    def __init__(self, sizes):
        super().__init__(sizes)
        self.sizes = sizes

    def sample(self, n=1, exclude=set()):
        if not (set(self.u) - set(exclude)):
            return {}
        return {
            name: T.randn(n, dims, device=self.device_param.device)
            for name, dims in self.sizes.items()
            if name not in exclude
        }


class BernoulliDistribution(Distribution):
    def __init__(self, sizes):
        super().__init__(sizes)
        self.sizes = nn.ParameterDict(
            {
                name: (
                    nn.Parameter(T.tensor([p]))
                    if len(T.tensor(p).shape) == 0
                    else T.tensor(p)
                )
                for name, p in sizes.items()
            }
        )

    def sample(self, n=1, exclude=set()):

        if not (set(self.u) - set(exclude)):
            return {}

        return {
            name: T.bernoulli(
                p.expand(n, len(p)),
            ).bool()
            for name, p in self.sizes.items()
            if name not in exclude
        }


class UniformDistribution(Distribution):
    def __init__(self, sizes):
        super().__init__(sizes)
        self.sizes = sizes

    def sample(self, n=1, exclude=set()):

        if not (set(self.u) - set(exclude)):
            return {}

        return {
            name: T.rand(n, dims, device=self.device_param.device)
            for name, dims in self.sizes.items()
            if name not in exclude
        }


class PoissonDistribution(Distribution):
    def __init__(self, name, rates):
        super().__init__([name])

        rates = T.tensor(rates)

        assert len(rates.shape) <= 1

        if len(rates.shape) == 0:
            rates = T.tensor([rates])

        self.name = name
        self.rates = rates

    def sample(self, n=1, exclude=set()):
        if not (set(self.u) - set(exclude)):
            return {}

        return (
            {
                self.name: T.poisson(self.rates.expand(n, len(self.rates))).to(
                    self.device_param.device
                )
            }
            if self.name not in exclude
            else {}
        )


class CategoricalDistribution(Distribution):
    def __init__(
        self,
        p: Dict[Hashable, Union[float, T.Tensor]] = {},
        logits: Dict[Hashable, Union[float, T.Tensor]] = {},
        sizes: Dict[Hashable, T.Size] = {},
        default_size: int = 1,
        grad: bool = False,
    ):
        """If p is a float between zero and one, the distribution will be binary."""

        assert p or logits or sizes
        assert not (p and logits)
        assert all(not isinstance(p, float) or p <= 1 for k, p in p.items())

        self.sizes = {
            k: sizes.get(k, default_size) for k in set(sizes).union(p).union(logits)
        }
        super().__init__(self.sizes)

        self.default_size = default_size
        if p:
            self.logits = {
                k: (
                    T.zeros(sizes[k], dtype=float)
                    if k not in p
                    else (
                        T.tensor([1 - p[k], p[k]]).log()
                        if isinstance(p[k], float) and p[k]
                        else (
                            p[k].log()
                            if isinstance(p[k], T.Tensor)
                            else T.tensor(p[k]).log()
                        )
                    )
                )
                for k in self.sizes
            }
        else:
            self.logits = {
                k: T.zeros(2, dtype=float) if k not in logits else logits[k]
                for k in self.sizes
            }
        self.grad = grad

        if grad:
            self.logits = nn.ParameterDict(
                {k: nn.Parameter(v) for k, v in self.logits.items()}
            )

    def sample(self, n=1, exclude=set()):
        if not (set(self.u) - set(exclude)):
            return {}

        return {
            k: T.distributions.Categorical(logits=self.logits[k])
            .sample((n, self.sizes.get(k, self.default_size)))
            .type_as(self.device_param)
            .long()
            for k in self.sizes
            if k not in exclude
        }


def get_probability_table(m: SCM, u=False, v=True):
    """
    Returns a probability table for the SCM.
    Only for discrete SCMs with a Categorical P(U).

    :param m: The SCM.
    :param u: Whether to include the U variables.
    :param v: Whether to include the V variables.
    """
    assert isinstance(m.pu, CategoricalDistribution)
    assert "probability" not in m.v
    assert u or v

    lp = {k: t - t.logsumexp(0) for k, t in m.pu.logits.items()}
    domains = {k: len(t) for k, t in lp.items()}
    rows = list(itertools.product(*[range(domains[k]) for k in m.pu]))
    obs = m.sample(u={k: T.tensor([r[i] for r in rows]) for i, k in enumerate(m.pu)})
    prob = [sum(lp[k][i] for k, i in zip(m.pu, r)).exp().item() for r in rows]

    u_list = list("u_%s" % u for u in m.pu)
    df = pd.DataFrame(
        data=[
            r + tuple(obs[k][i].item() for k in m.v) + (prob[i],)
            for i, r in enumerate(rows)
        ],
        columns=u_list + list(m.v) + ["probability"],
    )
    if u and v:
        return df
    elif u:
        return df.groupby(u_list).probability.sum().to_frame().reset_index()
    elif v:
        return df.groupby(list(m.v)).probability.sum().to_frame().reset_index()
