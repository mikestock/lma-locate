import raw_io
import glob

"""
This is a script used to test some/most features of the 
raw_io library.  It's not really a unit-test, but kinda
Also, I keep tearing it to the ground, and re-writing it.
-- this may not function in environments other than my own
"""

inPaths = glob.glob( '/data/LMA/iop3/*120000.dat') 
lmaFiles = []
epoch = 0
for inPath in inPaths:
    lmaFile = raw_io.RawLMAFile( inPath )
    lmaFiles.append( lmaFile )
    if lmaFile.startEpoch > epoch:
        epoch = lmaFile.startEpoch

epoch -=1
frames = [0]
for i in range( 601 ):
    epoch += 1
    #collect frames from all LMA files related to current epoch
    frames = []
    for lmaFile in lmaFiles:
        for iFrame in range( 1, len(lmaFile.statusPackets)):
            if lmaFile.statusPackets[iFrame].epoch == epoch:
                lmaFrame = lmaFile.read_frame( iFrame )
                frames.append( lmaFrame )
                break

    print ('Read %i frames for epoch %i'%(len(frames), epoch) )