from proteus import Domain, Context
from proteus.mprans import SpatialTools as st
from proteus import Gauges as ga
from proteus import WaveTools as wt
import numpy as np
from proteus.mprans import BodyDynamics as bd
from proteus.ctransportCoefficients import (smoothedHeaviside,
                                            smoothedHeaviside_integral)
import proteus.TwoPhaseFlow.TwoPhaseFlowProblem as TpFlow
from proteus import Gauges as ga



# Options (Geometry, Physical Properties, Waves, Numerical Options, Obstacle Dimentions)

opts=Context.Options([
    

    
    # Geometry
    ("tank_height",0.8,"Vertical Dimention of the tank"),
    ("Lback",4.0,"Horizontal Dimention of overtopping collection tank"),
    ("tank_depth", 0.5, "depth of the tank below zero level"),
    ("obs_depth", 0.4,"depth of the structure/obstacle below zero level"),
    ("tube", 0.1,"tube dimension"),
    ("deposit_width",5.0, "width of the tank used to collect the overtopped water"),
    ("wave_length",5.,"wave_length to define sponge length and tank dimensions"),


    # Physical Properties
    ("rho_0", 998.2, "Water density"),
    ("nu_0", 1.004e-6,"Water viscosity"),
    ("rho_1", 1.205, "Air density"),
    ("nu_1",1.5e-5, "Air viscosity"),
    ("sigma_01", 0.,"surface tension"),
    ("g", np.array([0., -9.805, 0.]), "gravity"),

    # Time and Duration
    ("Tstart", 0, "Start time"),
    ("Duration", 50., "Duration of the simulation"),
    ("Ntotalwaves",500,"totalnumber of waves"),
    ("x0", np.array([0.,0.,0.]), "Position vector for the time series"),

    # New Wave
    ("Tp", 2.326, "Peak wave period"),
    ("Hs", 0.1675, "Significant wave height"),
    ("mwl", 0.4, "Mean Water level"),
    ("depth", 0.4 , "Water depth"),
    ("waveDir", np.array([1.,0.,0.]),"Direction of the waves"),
    ("N", 1000, "Number of frequency components"),
    ("bandFactor", 2.0 ,"Spectal Band Factor"),
    ("spectName", "JONSWAP","Name of Spectral Distribution"),
    ("spectral_params",{"gamma": 3.3, "TMA":False,"depth": 0.4},"Spectral Distribution Characteristics"),
    ("crestFocus", True," True/False, enabling crest or trough focused wave"),
    ("xfocus", 0., "position of focused wave with respect to wavelength"),
    ("tfocus",10., "time that the wave appears at xfocus"),
    ("fast", True, " enabling random waves fast"),
    ("Nmax", 1000, "new wave is representative of Nmax waves in random sea"),
		
   # Numerical Options
    ("refinement_level", 200.,"he=wavelength/refinement_level"),
    ("cfl", 0.5,"Target cfl"),
    ("ecH", 1.5,"Smoothing Coefficient"),
    ("Np", 20. ," Output points per period Tp/Np" ),
    ("dt_init", 0.001 , "initial time step" ),
    ("waterLine_x", 10000, "used for the signed distance function"),
    
    # Obstacle Dimensions 
    ("structure_slope", 4, "1/slope"),
    ("structureCrestLevel", 0.5, "elevation of structure crest. Equal to Water depth + Rc (crest freeboard)")
    ])

# --- DOMAIN
domain = Domain.PlanarStraightLineGraphDomain()

# --- Wave length
wave_length=np.sqrt(9.81*opts.mwl)*opts.Tp

# --- Wave Input
wave=wt.NewWave(Tp=opts.Tp,
		Hs=opts.Hs,
		mwl=opts.mwl, 
		depth=opts.mwl,
		waveDir=opts.waveDir, 
		g=np.array([0.,-9.805,0.]), 
		N=opts.N,
 		bandFactor=opts.bandFactor,
		spectName=opts.spectName,
		spectral_params=opts.spectral_params, 
		crestFocus=opts.crestFocus,
		xfocus=np.array([opts.xfocus*wave_length,0.,0.]),
		tfocus=opts.tfocus,
		fast=opts.fast,
                Nmax=opts.Nmax
 		)     

# --- Domain
tank_dim = (3*wave_length+opts.structureCrestLevel*opts.structure_slope+opts.deposit_width,opts.tank_height)



# --- Tank Outline Geometry
                     
vertices=[[0.0,0.0], #0
            [wave_length,0],#1
            [wave_length,-opts.tank_depth],#2
            [3*wave_length+2*opts.tube+opts.structureCrestLevel*opts.structure_slope+1,-opts.tank_depth], #3
            [3*wave_length+2*opts.tube+opts.structureCrestLevel*opts.structure_slope+1,0.0], #4 after that abs zone
            [3*wave_length+2*opts.tube+opts.structureCrestLevel*opts.structure_slope+1+opts.Lback,0.0], #5
            [3*wave_length+2*opts.tube+opts.structureCrestLevel*opts.structure_slope+1+opts.Lback,opts.tank_height], #6
            [3*wave_length+2*opts.tube+opts.structureCrestLevel*opts.structure_slope+1,opts.tank_height],#7 abs zone upper boundary
            [wave_length,opts.tank_height], #8
            [0.0,opts.tank_height], #9
            [-wave_length,opts.tank_height], #10
            [-wave_length,0.], #11
            ]
         

vertexFlags=np.array([1, #0 
                        1, #1 lower boundary abs zone generation outlet
                        1, #2
                        1, #3
                        1, #4 lower boundary abs zone behind obstacle
                        1, #5 wall right boundary
                        3, #6 wall right boundary
                        3, #7 upper boundary abs zone behind obstacle
                        3, #8 upper boundary abs zone generation outlet
                        3, #9
                        4, #10 upper boundary abs zone generation inlet
                        4, #11 lower boundary abs zone generation inlet 
                        ])           

segments=[[0,1],
          [1,2],
          [2,3],
          [3,4],
          [4,5],
          [5,6],
          [6,7],
          [7,8],
          [8,9],
          [9,10],
          [10,11],
          [11,0],
          [0,9],
          [4,7],
              ]

segmentFlags=np.array([ 1, #[0,1] f
                        1, #[1,2] pipe left side
                        1, #[2,3] tank floor
                        1, #[3,4] pipe right side
                        1, #[4,5] f
                        2, #[5,6] wall after obstacle /right boundary
                        3, #[6,7] atm
                        3, #[7,8] atm
                        3, #[8,9] atm
                        3, #[9,10] atm
                        4, #[10,11]generation inlet
                        1, #[11,0] f
                        5, #[0,9] sponge
                        5, #[4,7] sponge after obstacle
                      ])



regions=[[5,0.3],[-0.5*wave_length,0.3],[3*wave_length+0.2+1+opts.structureCrestLevel*opts.structure_slope+2,0.4]]         
regionFlags =np.array([1,2,3])        



# --- Obstacle Geometry  
                      
obs_boundaryOrientations = {'obstacle': None}

obs_boundaryTags = {'obstacle' : 1,}

obs_vertices=[
            [wave_length+opts.tube,0],#0
            [wave_length+opts.tube,-opts.obs_depth],#1
            [3*wave_length+opts.tube+opts.structureCrestLevel*opts.structure_slope+1,-opts.obs_depth],#2
            [3*wave_length+opts.tube+opts.structureCrestLevel*opts.structure_slope+1,0.],#3
            [3*wave_length+opts.tube+opts.structureCrestLevel*opts.structure_slope,0.],#4
            [3*wave_length+opts.tube+opts.structureCrestLevel*opts.structure_slope,opts.structureCrestLevel],#5
            [3*wave_length+opts.tube,0],#6
            ]  

obs_vertexFlags=np.array([1, #11 
                        1, #12
                        1, #13
                        1, #14
                        1, #15
                        1, #16
                        1, #17
                        ])           

obs_segments=[[0,1],
              [1,2],
              [2,3],
              [3,4],
              [4,5],
              [5,6],
              [6,0],
              ]

obs_segmentFlags=np.array([ 1, #[11,12] 
                            1, #[12,13] 
                            1, #[13,14]
                            1, #[14,15]
                            1, #[15,16]
                            1, #[16,17]
                            1, #[17,11]
                            ])

obs_regions=[[2*wave_length, -0.2]]         
obs_regionFlags =np.array([1])        

obstacle = st.CustomShape(domain, vertices=obs_vertices, vertexFlags=obs_vertexFlags,
                      segments=obs_segments, segmentFlags=obs_segmentFlags,
                      regions=obs_regions, regionFlags=obs_regionFlags,
                      boundaryTags=obs_boundaryTags, 
                      boundaryOrientations=obs_boundaryOrientations)


obstacle.setHoles([[2*wave_length, -0.2]])


# --- Mesh Refinement
he=wave_length/opts.refinement_level
ecH=opts.ecH
smoothing=ecH*he

                          
# --- Boundary Conditions
boundaryOrientations = {'y-': np.array([0., -1.,0.]),
                        'x+': np.array([+1., 0.,0.]),
                        'y+': np.array([0., +1.,0.]),
                        'x-': np.array([-1., 0.,0.]),
                        'sponge': None,
                        'porousLayer': None,

                        'moving_porousLayer': None,
                       }

boundaryTags = {'y-' : 1,
                'x+' : 2,
                'y+' : 3,
                'x-' : 4,
                'sponge' : 5,
               }

tank = st.CustomShape(domain, vertices=vertices, vertexFlags=vertexFlags,
                      segments=segments, segmentFlags=segmentFlags,
                      regions=regions, regionFlags=regionFlags,
                      boundaryTags=boundaryTags, boundaryOrientations=boundaryOrientations)
               
# Tank
tank.BC['y+'].setAtmosphere()
tank.BC['y-'].setFreeSlip()
tank.BC['x+'].setFreeSlip()
tank.BC['x-'].setUnsteadyTwoPhaseVelocityInlet(wave, smoothing=smoothing, vert_axis=1)

tank.BC['sponge'].setNonMaterial()
for bc in obstacle.BC_list:
    bc.setFreeSlip()




# --- Generation & Absorption Zones Setup  

dragAlpha = 5*(2*np.pi/opts.Tp)/1e-6
he=float(wave_length/opts.refinement_level)

tank.setGenerationZones(flags=2, epsFact_porous=wave_length/2., center=(-wave_length/2,0.35), orientation=(1.,0.,0.), waves=wave, dragAlpha=dragAlpha)


tank.setAbsorptionZones(flags=3, epsFact_porous=wave_length/2., center=(3*wave_length+0.2+1+opts.structureCrestLevel*opts.structure_slope+2,0.4), orientation=(-1.,0.,0.), dragAlpha=dragAlpha)



# --- Initial Conditions

waterLine_x=opts.waterLine_x
waterLine_z = opts.mwl


def signedDistance(x):
    phi_x = x[0]- waterLine_x
    phi_y = x[1] - opts.mwl
    if phi_x < 0.0:
        if phi_y < 0.0:
            return max(phi_x, phi_y)
        else:
            return phi_y
    else:
        if phi_y < 0.0:
            return phi_x
        else:
            return np.sqrt(phi_x ** 2 + phi_y ** 2)


class P_IC:
    def __init__(self):
        self.waterLevel=opts.mwl
    def uOfXT(self,x,t):
        if signedDistance(x) < 0:
            return -(opts.tank_height - opts.mwl)*opts.rho_1*opts.g[1] - (opts.mwl - x[1])*opts.rho_0*opts.g[1]
        else:
            return -(opts.tank_height - opts.mwl)*opts.rho_1*opts.g[1]
class AtRest:
    def uOfXT(self, x, t):
        return 0.0

class VOF_IC:
    def uOfXT(self,x,t):
        return smoothedHeaviside(opts.ecH * he, signedDistance(x))

class LS_IC:
    def uOfXT(self,x,t):
        return signedDistance(x)




# Two Phase Flow
dt_output = opts.Tp/opts.Np


# Two-phase flow problem
myTpFlowProblem = TpFlow.TwoPhaseFlowProblem()
myTpFlowProblem.domain = domain
myTpFlowProblem.outputStepping.final_time = opts.Duration
myTpFlowProblem.outputStepping.dt_init = opts.dt_init
myTpFlowProblem.outputStepping.dt_output = dt_output
myTpFlowProblem.outputStepping.systemStepExact = True

physics = myTpFlowProblem.SystemPhysics
physics.setDefaults()
physics.useDefaultModels(flowModel=0, interfaceModel=0)
myTpFlowProblem.SystemNumerics.cfl = opts.cfl

m = physics.modelDict
m['flow'].p.initialConditions['p'] = P_IC()
m['flow'].p.initialConditions['u'] = AtRest()
m['flow'].p.initialConditions['v'] = AtRest()
m['vof'].p.initialConditions['vof'] = VOF_IC()
m['ncls'].p.initialConditions['phi'] = LS_IC()
m['rdls'].p.initialConditions['phid'] = LS_IC()
m['mcorr'].p.initialConditions['phiCorr'] = AtRest()


myTpFlowProblem.SystemNumerics.useSuperlu = False
physics.rho_0 = opts.rho_0
physics.rho_1 = opts.rho_1
physics.nu_0 = opts.nu_0
physics.nu_1 = opts.nu_1
physics.surf_tension_coeff = opts.sigma_01

m['rdls'].p.coefficients.epsFact=0.75
m['rdls'].n.maxLineSearches=0
m['rdls'].n.maxNonlinearIts=50

#Assemble domain
domain.MeshOptions.he = he
st.assembleDomain(domain)
m['flow'].auxiliaryVariables += domain.auxiliaryVariables['twp']



##################################################################################





