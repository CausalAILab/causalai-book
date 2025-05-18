from src.task.classes.task import TaskSetDefinition


experimentsDefName = 'experiments'
observationsDefName = 'observations'
experimentFieldSuffix = '_exp'
observedFieldSuffix = '_obs'
targetPopulationExpDefName = '*'
targetPopulationExpDef = TaskSetDefinition('*_exp', 'Z^*')
targetPopulationObsDef = TaskSetDefinition('*_obs', 'P(v)')