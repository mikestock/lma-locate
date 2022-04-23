import raw_io
import phasor
import glob

"""
This is a script used to test some/most features of the 
phasor library.  It's not really a unit-test, but kinda
Also, I keep tearing it to the ground, and re-writing it.
-- this may not function in environments other than my own
"""

inLmaPaths = glob.glob( '/data/LMA/iop3/*120000.dat') 
inLocPath  = '/data/LMA/iop3/mobile.loc'

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

#loop over epochs, and make groups of frames to initialize Phasor objects with
epoch -=1
for iLoop in range( 10 ):
    epoch += 1
    frames = {}
    for lmaFile in lmaFiles:
    
        #use the lookup table to get the frame number
        if epoch in lmaFile.frameEpochs:
            iFrame = lmaFile.frameEpochs[epoch]
            frame = lmaFile.read_frame( iFrame )
            #frame goes into dict
            frames[ frame.id ] = frame
    
    p = phasor.Phasor( frames, locFile=locFile, cartesian=locFile.network.cartesian )

    

