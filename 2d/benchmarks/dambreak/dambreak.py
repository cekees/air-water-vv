"""
Dambreak flow - Collagrosi and Landrini (2003)
"""
import numpy as np
from math import sqrt
from proteus import (Domain, Context,
                     FemTools as ft,
                     #SpatialTools as st,
                     MeshTools as mt,
                     WaveTools as wt)
from proteus.mprans import SpatialTools as st
from proteus.Profiling import logEvent
from proteus.mprans.SpatialTools import Tank2D
from proteus.ctransportCoefficients import (smoothedHeaviside,
                                            smoothedHeaviside_integral)
import proteus.TwoPhaseFlow.TwoPhaseFlowProblem as TpFlow


# Context Options

opts=Context.Options([
    # water column 
    ("mwl", 0.6, "Height of water column in m"),
    ("water_width", 1.2, "Width of  water column in m"),
    ("rho_0",998.2,"water density"),
    ("nu_0",1.004e-6,"water viscosity"),
    ("rho_1",1.205,"air density"),
    ("nu_1",1.500e-5,"air viscosity"),
    ("sigma",0.0, "surface tension"),
    # tank
    ("tank_dim", (3.22, 1.8), "Dimensions of the tank  in m"),
    #gravity 
    ("g",(0,-9.81,0), "Gravity vector in m/s^2"),
    # gauges
    ("gauge_output", True, "Produce gauge data"),
    ("gauge_location_p", (3.219999, 0.12, 0), "Pressure gauge location in m"),
    # mesh refinement and timestep
    ("he",0.02,"mesh cell size"),
    ("cfl", 0.33 ,"Target cfl"),
    ("ecH", 3,"Smoothing Coefficient"),
    # run time options
    ("duration",10.,"duration of simulation"),
    ("T", 0.09 ,"Simulation time in s"),
    ("dt_fixed", 0.01, "Fixed time step in s"),
    ("dt_init", 0.001 ,"Maximum initial time step in s"),
    ("dt_output",0.05, "output stepping")
    ])

# Domain 
domain = Domain.PlanarStraightLineGraphDomain()

# Tank
tank = Tank2D(domain, opts.tank_dim)

# Gauges
if opts.gauge_output:
    tank.attachPointGauges('twp',
        	           gauges = ((('p',), (opts.gauge_location_p,)),),
                           activeTime=(0, opts.T),
                           sampleRate=0,
                           fileName='pressureGauge.csv'
                           )

# Boundary Conditions 
tank.BC['y+'].setAtmosphere()
tank.BC['y-'].setFreeSlip()
tank.BC['x+'].setFreeSlip()
tank.BC['x-'].setFreeSlip()

# Mesh 
domain.MeshOptions.he = opts.he


# Initial conditions
def signedDistance(x):
    phi_x = x[0] - opts.water_width
    phi_z = x[1] - opts.mwl
    if phi_x < 0.0:
        if phi_z < 0.0:
            return max(phi_x, phi_z)
        else:
            return phi_z
    else:
        if phi_z < 0.0:
            return phi_x
        else:
            return sqrt(phi_x ** 2 + phi_z ** 2)

class P_IC:
    def __init__(self):
        self.mwl=opts.mwl
    def uOfXT(self,x,t):
        if signedDistance(x) < 0:
            return -(opts.tank_dim[1] - opts.mwl)*opts.rho_1*opts.g[1] - (opts.mwl - x[1])*opts.rho_0*opts.g[1]
        else:
            return -(opts.tank_dim[1] - opts.mwl)*opts.rho_1*opts.g[1]
class AtRest:
    def uOfXT(self, x, t):
        return 0.0

class VOF_IC:
    def uOfXT(self,x,t):
        return smoothedHeaviside(opts.ecH * opts.he, signedDistance(x))

class LS_IC:
    def uOfXT(self,x,t):
        return signedDistance(x)

#Assemble domain
st.assembleDomain(domain)

# Two-phase flow problem (RANS2P + VOF/NCLS/RDLS/MCorr)
myTpFlowProblem = TpFlow.TwoPhaseFlowProblem()
myTpFlowProblem.domain = domain

myTpFlowProblem.outputStepping.final_time = opts.duration
myTpFlowProblem.outputStepping.dt_init = opts.dt_init
myTpFlowProblem.outputStepping.dt_output = opts.dt_output
myTpFlowProblem.outputStepping.systemStepExact = True

physics = myTpFlowProblem.SystemPhysics
physics.setDefaults()
physics.useDefaultModels(flowModel=0, interfaceModel=0)
physics.rho_0 = opts.rho_0  # water
physics.nu_0 = opts.nu_0
physics.rho_1 = opts.rho_1  # air
physics.nu_1 = opts.nu_1
physics.surf_tension_coeff = opts.sigma
physics.gravity = np.array(opts.g)

myTpFlowProblem.SystemNumerics.cfl = opts.cfl
myTpFlowProblem.SystemNumerics.useSuperlu = False

m = physics.modelDict
m['flow'].p.initialConditions['p'] = P_IC()
m['flow'].p.initialConditions['u'] = AtRest()
m['flow'].p.initialConditions['v'] = AtRest()
m['vof'].p.initialConditions['vof'] = VOF_IC()
m['ncls'].p.initialConditions['phi'] = LS_IC()
m['rdls'].p.initialConditions['phid'] = LS_IC()
m['mcorr'].p.initialConditions['phiCorr'] = AtRest()

m['flow'].auxiliaryVariables += domain.auxiliaryVariables['twp']
