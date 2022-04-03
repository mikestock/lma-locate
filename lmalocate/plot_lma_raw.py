import matplotlib.pyplot as plt
import raw_io
import os, sys, time
import numpy as np

if __name__ == '__main__':
    """
    There's nothing to import, so I'm not sure why __name__ wouldn't be __main__
    """

    if len( sys.argv ) < 2:
        print ('Usage: python plot_lma_raw.py <LMA RAW FILE PATH>')
        sys.exit()
    inPath = sys.argv[-1]
    if not os.path.exists( inPath ):
        print ('Input path %s does not exist'%inPath)
        sys.exit()

    #open the file
    lmaRawData = raw_io.RawLMA( inPath )

    #loop over each second and collect information about things
    threshold = []
    aboveThresh = []
    triggers  = []
    power     = []
    seconds   = []
    tStart = time.time()
    for i in range( 1, len( lmaRawData.statusLocations ) ):
        print(i)
        #looking at the form of this, it's kinda stupid
        df, statusPacket = lmaRawData.read_frame( i )

        power.append( [df['power'].min(), df['power'].max()] )
        aboveThresh.append( [df['aboveThresh'].min(), df['aboveThresh'].max()] )
        threshold.append( 0.488*statusPacket.threshold-111.0  )
        triggers.append( len(df) )
        seconds.append( i )
    print( 'fileRead in %1.2f seconds'%(time.time()-tStart) )

    aboveThresh = np.array( aboveThresh )
    power       = np.array( power )

    fig, ax = plt.subplots( 2,1, figsize=(5,10) )
    ax[0].fill_between( seconds, aboveThresh[:,1], aboveThresh[:,0], label='Above Threshold' )
    ax[0].plot( seconds, triggers, 'r-', label='Trigger Count' )
    ax[0].legend( loc='upper right')
    ax[0].set_xlabel( 'Time [s]')
    ax[0].set_ylabel( 'Count' )

    ax[1].fill_between( seconds, power[:,1], power[:,0], label='Trigger Power' )
    ax[1].plot( seconds, threshold, 'r-', label='Threshold' )
    ax[1].legend( loc='upper right')
    ax[1].set_xlabel( 'Time [s]')
    ax[1].set_ylabel( 'Power [dBm]' )

    plt.show()



    #plot figure showing threshold and power in dBm

