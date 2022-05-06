import raw_io
import phasor
import glob
import numpy as np
from common import *
from scipy import optimize

"""
This is a script used to test some/most features of the 
phasor library.  It's not really a unit-test, but kinda
Also, I keep tearing it to the ground, and re-writing it.
-- this may not function in environments other than my own
"""

inLmaPaths = glob.glob( '/data/LMA/iop3/*120000.dat') 
inLocPath  = '/data/LMA/iop3/mobile.loc'

windowLength = 2000000

#load up the location file
locFile = raw_io.LocFile( inLocPath )

#load up the LMA raw data files
lmaFiles = []
epoch = -1
for inPath in inLmaPaths:
    lmaFile = raw_io.RawLMAFile( inPath )
    lmaFiles.append( lmaFile )
    #get the processing epoch start
    if epoch < 0 or lmaFile.startEpoch < epoch: 
        epoch = lmaFile.startEpoch

def tdoa_resid( x, data ):
    geodetic = (x[0],x[1],7000)
    
    
    #distance to the reference station doesn't change, 
    #so we can just calculate it once
    D0 = distance.vincenty( geodetic, data[0][1:] )
    D0 = distance.distance3d( D0, 7000-data[0,3] )
    t0 = data[0,0]
    
    i = 1
    resid = []
    while i < len(data):
        Di = distance.vincenty( geodetic, data[i][1:] )
        Di = distance.distance3d( Di, 7000-data[i,3] )
        ti = data[i,0]

        resid.append( D0-Di + Cns*(t0-ti) )
        i += 1
    return np.array(resid)

def toa_resid( x, data ):
    # print(x)
    resid = []
    for pk in data:
        D = distance.euclidean( x[1:], pk[1:] )
        r = x[0]+D/Cns - pk[0]
        resid.append( r )
    return np.array( resid )

#loop over epochs, and make groups of frames to initialize Phasor objects with
epoch -=1
centers = []
for iLoop in range( 10 ):
    epoch += 1
    frames = {}
    for lmaFile in lmaFiles:
    
        #use the lookup table to get the frame number
        if epoch in lmaFile.frameEpochs:
            iFrame = lmaFile.frameEpochs[epoch]
            frame = lmaFile.read_frame( iFrame )
            #decimate the crap of out this so we don't have too many initial guesses and everything is fastpanda
            frame.decimate( windowLength )
            #frame goes into dict
            frames[ frame.id ] = frame
    
    p = phasor.Phasor( frames, locFile=locFile, cartesian=locFile.network.cartesian, windowLength=windowLength )

    #for each guess, make a solution
    solutions = []
    for guess in p.guesses:
        #the guess is an array of indices, pull the peak information
        peaks = p.sortedPeaks[guess]
        #we need to get the time of the event from this
        nano = np.median( peaks[:,0] )
        s = phasor.Solution( peaks, nano, phasor=p )
        solutions.append( s )
        # print ( '%9i'%np.sqrt((s.calc_residual()**2).sum()) )

    solutions.sort()
    
    for s in solutions:
        data = []
        for pk in s.selectedPeaks:
            sensorId = chr( pk[1] )
            nano     = pk[2]
            lat,lon,alt = s.loc.sensors[ sensorId ].geodetic 
            x,y,z       = s.loc.sensors[ sensorId ].cartesian 
            data.append( [nano, x, y, z] ) 
        data = np.array( data )
        x0 = s.nano, s.cartesian[0], s.cartesian[1], s.cartesian[2]
        geodetic0 = xyz2latlonalt( *s.cartesian )
        try:
            sol  = optimize.root( toa_resid, x0, args=(data,), method='lm' )
            x1 = sol.x
            r = toa_resid( x1, data)
            r = np.sqrt( (r**2).mean() )    #rms residual, in ns
            geodetic1 = xyz2latlonalt( *x1[1:] )
            if sol.success:
                D = distance.vincenty( geodetic0, geodetic1 )
                if D < 250000 and r < 10000:
                    centers.append( (geodetic1[0], geodetic1[1], r ) )
            print (s, repr(sol.success).rjust(5),  '%5.1f, %6.1f, %7i'%xyz2latlonalt( *sol.x[1:] ), int(r) )

        # x0   = np.array( xyz2latlonalt( *s.cartesian )[:2] )
        # try:
        #     sol  = optimize.root( tdoa_resid, x0, args=(data,), method='lm' )
           
        #     if sol.success:
        #         x = sol.x
        #         geodetic1 = [x0[0], x0[1], 0 ]
        #         geodetic2 = [x[0], x[1], 0 ]
        #         D=distance.vincenty( geodetic1, geodetic2 )
        #         if D < 250000:
        #             r = tdoa_resid( x, data)
        #             r = np.sqrt( (r**2).mean() )    #rms residual, in ns
        #             if r < 10000:
        #                 centers.append( (x[0], x[1], r ) )
        #             print (s, sol.success, sol.x, r )
        except:
            #Vincenti seems to sometimes have issues, likely when the optimizer asks for distances from lat/lon out of bounds for the planet
            # print( s, 'something went wrong' )
            pass
    

