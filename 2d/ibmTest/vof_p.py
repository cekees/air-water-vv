from proteus.default_p import *
from proteus.ctransportCoefficients import smoothedHeaviside
from proteus.mprans import VOF3P
from proteus import Context

ct = Context.get()
domain = ct.domain
nd = domain.nd
mesh = domain.MeshOptions


genMesh = mesh.genMesh
movingDomain = ct.movingDomain
T = ct.T

LevelModelType = VOF3P.LevelModel



coefficients = VOF3P.Coefficients(LS_model=1,
                                  V_model=4,
                                  RD_model=2,
                                  ME_model=0,
                                  checkMass=True,
                                  useMetrics=ct.useMetrics,
                                  epsFact=3,
                                  sc_uref=ct.vof_sc_uref,
                                  sc_beta=ct.vof_sc_beta,
                                  movingDomain=ct.movingDomain)

dirichletConditions = {0: lambda x, flag: domain.bc[flag].vof_dirichlet.init_cython()}

advectiveFluxBoundaryConditions = {0: lambda x, flag: domain.bc[flag].vof_advective.init_cython()}

diffusiveFluxBoundaryConditions = {0: {}}

class PerturbedSurface_H:
    def uOfXT(self,x,t):
        return smoothedHeaviside(3*ct.he,x[1]-ct.waterLevel)

initialConditions  = {0:PerturbedSurface_H()}