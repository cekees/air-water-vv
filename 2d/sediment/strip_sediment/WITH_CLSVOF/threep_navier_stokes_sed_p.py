from proteus import *
from proteus.default_p import *
from tank import *
from proteus.mprans import RANS3PSed
from proteus import Context
ct = Context.get()

LevelModelType = RANS3PSed.LevelModel

if ct.sedimentDynamics:
    if ct.useCLSVOF:
        VOS_model=0
        CLSVOF_model=1
        VOF_model=None
        LS_model=None
        RD_model=None
        MCORR_model=None
        SED_model=2
        V_model=3
        PINC_model=4
        PRESSURE_model=5
        PINIT_model=6
    else:
        VOS_model=0
        VOF_model=1
        LS_model=2
        RD_model=3
        MCORR_model=4
        SED_model=5
        V_model=6
        PINC_model=7
        PRESSURE_model=8
        PINIT_model=9
else:
    VOS_model=None
    SED_model=None
    VOF_model=0
    LS_model=1
    RD_model=2
    MCORR_model=3
    V_model=4
    PINC_model=5
    PRESSURE_model=6
    PINIT_model=7

if useOnlyVF:
    LS_model = None
else:
    LS_model = 2
if useRANS >= 1:
    Closure_0_model = 5; Closure_1_model=6
    if useOnlyVF:
        Closure_0_model=2; Closure_1_model=3
    if movingDomain:
        Closure_0_model += 1; Closure_1_model += 1
else:
    Closure_0_model = None
    Closure_1_model = None


coefficients = RANS3PSed.Coefficients(epsFact=epsFact_viscosity,
                                      sigma=0.0,
                                      rho_0 = rho_0,
                                      nu_0 = nu_0, 
                                      rho_1 = rho_1,
                                      nu_1 = nu_1,
                                      rho_s = rho_s,
                                      g=g,
                                      nd=nd,
                                      ME_model=SED_model,
                                      PRESSURE_model=PRESSURE_model,
                                      FLUID_model=V_model,
                                      VOS_model=VOS_model,
                                      CLSVOF_model=CLSVOF_model,
                                      VOF_model=VOF_model,
                                      LS_model=LS_model,
                                      Closure_0_model=Closure_0_model,
                                      Closure_1_model=Closure_1_model,
                                      epsFact_density=epsFact_density,
                                      stokes=False,
                                      useVF=True,
                                      useRBLES=useRBLES,
                                      useMetrics=useMetrics,
                                      eb_adjoint_sigma=1.0,
                                      eb_penalty_constant=weak_bc_penalty_constant,
                                      forceStrongDirichlet=ns_forceStrongDirichlet,
                                      turbulenceClosureModel=ns_closure,
                                      movingDomain=movingDomain,
                                      dragAlpha=dragAlpha,
                                      PSTAB=ct.opts.PSTAB,
                                    aDarcy = ct.sedClosure.aDarcy,
                                    betaForch = ct.sedClosure.betaForch,
                                    grain = ct.sedClosure.grain,
                                    packFraction = ct.sedClosure.packFraction,
                                    maxFraction = ct.sedClosure.maxFraction,
                                    frFraction = ct.sedClosure.frFraction,
                                    sigmaC =ct.sedClosure.sigmaC,
                                    C3e = ct.sedClosure.C3e,
                                    C4e = ct.sedClosure.C4e,
                                    eR = ct.sedClosure.eR,
                                    fContact = ct.sedClosure.fContact,
                                    mContact = ct.sedClosure.mContact,
                                    nContact = ct.sedClosure.nContact,
                                    angFriction = sedClosure.angFriction,
                                    vos_function = ct.vos_function,
                                    staticSediment = False,
                                    vos_limiter = ct.sedClosure.vos_limiter,
                                    mu_fr_limiter = ct.sedClosure.mu_fr_limiter,
                                    )

dirichletConditions = {0: lambda x, flag: domain.bc[flag].us_dirichlet.init_cython(),
                       1: lambda x, flag: domain.bc[flag].vs_dirichlet.init_cython()}

advectiveFluxBoundaryConditions = {0: lambda x, flag: domain.bc[flag].us_advective.init_cython(),
                                   1: lambda x, flag: domain.bc[flag].vs_advective.init_cython()}

diffusiveFluxBoundaryConditions = {0: {0: lambda x, flag: domain.bc[flag].us_diffusive.init_cython()},
                                   1: {1: lambda x, flag: domain.bc[flag].vs_diffusive.init_cython()}}

if nd == 3:
    dirichletConditions[2] = lambda x, flag: domain.bc[flag].ws_dirichlet.init_cython()
    advectiveFluxBoundaryConditions[2] = lambda x, flag: domain.bc[flag].ws_advective.init_cython()
    diffusiveFluxBoundaryConditions[2] = {2: lambda x, flag: domain.bc[flag].ws_diffusive.init_cython()}

class AtRest:
    def __init__(self):
        pass
    def uOfXT(self,x,t):
        return 0.0

initialConditions = {0:AtRest(),
                     1:AtRest()}
