from proteus import *
from proteus.default_p import *
from math import *
from floating_bar import *
from proteus.mprans import RDLS
"""
The redistancing equation in the sloshbox test problem.
"""

LevelModelType = RDLS.LevelModel

coefficients = RDLS.Coefficients(applyRedistancing=applyRedistancing,
                                 epsFact=epsFact_redistance,
                                 nModelId=2,
                                 rdModelId=3,
                                 useMetrics=useMetrics)

def getDBC_rd(x,flag):
    pass
    
dirichletConditions     = {0:getDBC_rd}
weakDirichletConditions = {0:RDLS.setZeroLSweakDirichletBCsSimple}

advectiveFluxBoundaryConditions =  {}
diffusiveFluxBoundaryConditions = {0:{}}

class PHI_IC:       
    def uOfXT(self,x,t):
        return x[2]-waterLevel

initialConditions  = {0:PHI_IC()}
