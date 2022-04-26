import raw_io
import glob

"""
This is a script used to test some/most features of the 
raw_io library.  It's not really a unit-test, but kinda
Also, I keep tearing it to the ground, and re-writing it.
-- this may not function in environments other than my own
"""

#load in a whole bunch of raw data files
inPaths = glob.glob( '/data/LMA/iop3/*120000.dat') 
lmaFiles = []
epoch = 0
for inPath in inPaths:
    lmaFile = raw_io.RawLMAFile( inPath )
    lmaFiles.append( lmaFile )

    #getting the startEpoch this way is a little dangerous 
    #if all the files don't start at the same time
    if lmaFile.startEpoch > epoch:
        epoch = lmaFile.startEpoch

epoch -=1
frames = [0]
for i in range( 601 ):
    epoch += 1
    #collect frames from all LMA files related to current epoch
    frames = []
    stations = []
    for lmaFile in lmaFiles:

        #the epoch we're looking for should be in the 
        #frameEpochs table, hopefully
        if epoch in lmaFile.frameEpochs:
            #great, now we don't have to loop over all the statuses
            iFrame = lmaFile.frameEpochs[epoch]
            lmaFrame = lmaFile.read_frame( iFrame )
            
            #create station from frame information
            stations.append( raw_io.Station( id=lmaFrame.id, geodetic=lmaFrame.geodetic, cartesian=lmaFrame.cartesian, delay=0) )
            #decimate the frame
            lmaFrame.decimate( 2000000 )

            #append frame to list, for reasons
            frames.append( lmaFrame )
        #else, this epoch doesn't exist, boo

    #all of the epochs should have 7 files, 
    #except of the last one which has 0
    print ('Read %i frames for epoch %i'%(len(frames), epoch) )

    #we should be able to create a locFile from these frames
    #it should at least not error
    locFile = raw_io.LocFile()
    for station in stations:
        locFile.add( station )
