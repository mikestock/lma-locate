#!/usr/bin/python
#
"""io
Reads and writes various LMA data formats
Support inlcudes:
In:
  raw lma v8 (80us)
  raw lma v9 (10us)
"""

import struct, os, sys, time, warnings
import numpy as np


dataFrameDtype = [ ('nano', 'i'),
                   ('power', 'f'),
                   ('aboveThresh', 'i')]

class RawLMA:

    def __init__ (self, inputPath ):
        """
        inputPath = path to lma data file
        """

        #lat/lon information
        #we could get this from a location file as well, but it's contained 
        #in the V10+ data files
        self.gpslat = 0 #these guys need to be converted
        self.gpslon = 0
        self.gpsalt = 0
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.vel = 0
        self.brg = 0

        self.dataVersion = None #there's a number of different LMA raw data versions
        self.inputPath    = inputPath
        #try opening the inputPath, that should work if it exists
        if os.path.exists( self.inputPath ):
            self.inputFile = open( self.inputPath, 'rb' )
            self.inputFileSize = os.path.getsize( self.inputPath )
        else:
            raise Exception( 'RawLMA.__init__: inputPath does not exist: %s'%self.inputPath )
        
        #we need to find the file locations of each of the status words
        #these will break up the file into 1 second chunks
        self.find_status() 

    def convert_latlon( self, gpsInt):
        """
        this takes in the gps integer value used for latitude and longitude, and 
        converts it into decimal degrees
        """

        #is the number negative?
        if gpsInt >> 31 == 1:
            #yes it is
            gpsInt -= 1<<32
        
        latlon = gpsInt *90/324000000.0
        return latlon

    def find_status( self ):
        self.statusLocations = []
        self.statusPackets   = []
        self.inputFile.seek( 0 )

        #the LMA raw data uses the first bit of the data words to make a pattern
        #the data packets have first bytes that go 0, 1, 0
        #the status packets have first bytes that go 1,1,1,1,1,1,1,1,1
        #so, we can struct to decode the data, and test if the numbers are 
        #positive or negative to determine if we've found a status word

        #the status packets do include how many data packets they include, 
        #but, the status comes at the end of the data.  We need to scan backwards 
        #from the end of the file, but to do that we need to know the data version
        #so we know how big a status packet is
        statusPacket = StatusPacket( self.inputFile.read(18) )
        self.version = statusPacket.version
        if self.version >= 10:
            self.statusSize = 18
        else:
            self.statusSize = 12

        #now search for the remaining status packets in reverse, start by 
        #seeking to the end of the file
        self.inputFile.seek(0, 2)
        while self.inputFile.tell() > self.statusSize:
            self.inputFile.seek( -self.statusSize, 1 )
            self.statusLocations.append( self.inputFile.tell() )
            statusPacket = StatusPacket( self.inputFile.read(self.statusSize) )
            self.statusPackets.append( statusPacket )

            #handle GPS info
            if statusPacket.second %12 ==0:
                #lat bytes 4/3
                self.gpslat = (statusPacket.gpsInfo<<16) | (self.gpslat &0xFFFF)
                self.lat = self.convert_latlon( self.gpslat )
            elif statusPacket.second %12 ==1:
                #lat bytes 2/1
                self.gpslat = (statusPacket.gpsInfo) | (self.gpslat &0xFFFF0000)
                self.lat = self.convert_latlon( self.gpslat )
            elif statusPacket.second %12 ==2:
                #lon bytes 4/3
                self.gpslon = (statusPacket.gpsInfo<<16) | (self.gpslon &0xFFFF)
                self.lon = self.convert_latlon( self.gpslon )
            elif statusPacket.second %12 ==3:
                #lon bytes 2/1
                # self.gpslon = (statusPacket.gpsInfo<<16) | (self.gpslon &0xFFFF)
                self.gpslon = (statusPacket.gpsInfo) | (self.gpslon &0xFFFF0000)
                self.lon = self.convert_latlon( self.gpslon )
            elif statusPacket.second %12 ==4:
                #alt bytes 4/3
                self.gpsalt = (statusPacket.gpsInfo<<16) | (self.gpsalt &0xFFFF)
                self.alt = self.gpsalt/100.0
            elif statusPacket.second %12 ==5:
                #alt bytes 2/1
                self.gpsalt = (statusPacket.gpsInfo) | (self.gpsalt &0xFFFF0000)
                self.alt = self.gpsalt/100.0
            elif statusPacket.second %12 ==6:
                #vel bytes 4/3
                self.vel = (statusPacket.gpsInfo<<16) | (self.vel &0xFFFF)
            elif statusPacket.second %12 ==7:
                #vel bytes 2/1
                self.vel = (statusPacket.gpsInfo) | (self.vel &0xFFFF0000)
            elif statusPacket.second %12 ==8:
                #brg 
                self.brg = statusPacket.gpsInfo
            elif statusPacket.second %12 ==9:
                #vis/tracked satellites
                self.satTracked = (statusPacket.gpsInfo>>8) &0xFF
                self.satVisible = statusPacket.gpsInfo &0xFF
            elif statusPacket.second %12 ==10:
                #statellite stat?
                self.satStat = statusPacket.gpsInfo &0xFFF
            elif statusPacket.second %12 ==11:
                #temperature 
                self.temp = (statusPacket.gpsInfo>>8)-40

            #determine how far back to seek
            if self.inputFile.tell() > statusPacket.triggerCount * 6 + self.statusSize:
                self.inputFile.seek( -statusPacket.triggerCount * 6 -self.statusSize, 1)
            else:
                #this really shouldn't happen
                #because the raw file should start with a status
                #(and we used that fact to get the version)
                warnings.warn( "RawLMA.find_status encountered condition which shouldn't happen" )
                break

        #we didn't add the first status packet to the list, and that's ok 
        #because there are no data packets associated with it (they're in the previous file)
        #but, we would like to add in the location, to make later math a little easier
        self.statusLocations.append( 0 )
        self.statusPackets.append( None )   #the first status shouldn't be used

        #the information on the status packets is reversed
        self.statusLocations.reverse()
        self.statusPackets.reverse()

    def read_frame( self, iStatus):
        """
        Read in all the datapackets associated with the ith status message

        returns a structured numpy array
        """
        

        if iStatus <= 0 or iStatus >= len(self.statusLocations) :
            raise Exception( "Can't read the %ith collection of data, choose number between 1 and %i"%(iStatus, len(self.statusLocations)-1) )


        #we get the start and end point of our read from the statusLocations
        #those are file locations.  We need to offset the start point by the 
        #size of 1 statusPacket though
        readStart = self.statusLocations[ iStatus-1 ]+self.statusSize
        readEnd   = self.statusLocations[ iStatus ]

        #Get some information we'll need from the assoicated status packet
        statusPacket = self.statusPackets[ iStatus ]
        version   = statusPacket.version    #needed for dataPacket format
        phaseDiff = statusPacket.phaseDiff  #only if we want good timinh
        triggerCount= statusPacket.triggerCount #this is how many dataPackets there will be

        #data is going into this thing.  
        #the structured type is needlessly fancy.  Could be worse and be a pandas dataframe thing
        dataFrame = np.zeros( triggerCount, dtype=dataFrameDtype)

        self.inputFile.seek( readStart )
        for i in range( triggerCount ):
            if self.inputFile.tell() >= readEnd:
                raise Exception( "RawLMA.read - data packet reading is out of bounds, %i>=%i"%(self.inputFile.tell(), readEnd))
            d = DataPacket( self.inputFile.read(6), version=version, phaseDiff=phaseDiff )
            
            dataFrame['nano'][i]        = d.nano
            dataFrame['power'][i]       = d.power
            dataFrame['aboveThresh'][i] = d.aboveThresh
        
        return dataFrame, statusPacket

class StatusPacket:

    #There are a lot of masks used in doing this the Rison way
    #Here's a cheat sheet
    #0x1  0001
    #0x3  0011
    #0x7  0111
    #0xF  1111
    #0x8  1000
    #0x4  0100
    #0x2  0010
    #0x1  0001

    def __init__( self, inputString ):

        self.inputString = inputString
        #decode the words
        self.words = struct.unpack( '<9h', inputString )

        if not all( [v<0 for v in self.words] ):
            raise Exception( "Malformed status packet doesn't follow bit pattern" )
        #get the version, we do this with masks and fun stuff
        self.version = (self.words[0]>>7)	&0x3f	#version
        self.decode()

    def decode( self ):
        if self.version == 10 or self.version == 11:
            self.decode_1011()
        else:
            raise Exception( 'Unknown raw data version %i'%self.version )

    def decode_1011( self ):
        #reference data_format_v12.pdf
        self.year         =  self.words[0] &0x7F + 2000
        self.threshold    =  self.words[1] &0xFF
        self.fifoStatus   = (self.words[2]>>12)&0x07
        self.second       = (self.words[2]>>6 )&0x3F
        self.minute       =  self.words[2] &0x3F
        self.hour         = (self.words[3]>>9)&0x1F
        self.day          = (self.words[3]>>4)&0x1F
        self.month        =  self.words[3] &0x0F
        self.triggerCount =  self.words[4] &0x3FFF
        self.id           = (self.words[1]>>5)&0x80 | (self.words[5]>>8)&0x7F
        #in typical Bill fashion, he's offset the ID by 64, to skip the non-letter values
        #in less Bill fashion, he used 8 bits to encode, even though ASCII only has 128 values
        #(even less if you skip the first 64 characters)
        self.id           = chr(self.id+64)
        self.phaseDiff    =  self.words[6] &0x7FFF
        #sign bit stored elsewhere
        if (self.words[1]>>14)&0x1 == 1:
            self.phaseDiff *= -1
        
        ###
        # GPS info is updated on a 12 second cycle
        # TODO - handle the 12 second cycle
        # self.gpsInfo      = (self.words[7] &0x7FFF) | (self.words[1]<<2)&0x8000
        self.gpsInfo      = (self.words[7] &0x7FFF) | (self.words[1]&0x2000)<<2

class DataPacket:

    #There are a lot of masks used in doing this the Rison way
    #Here's a cheat sheet
    #0x1  0001
    #0x3  0011
    #0x7  0111
    #0xF  1111
    #0x8  1000
    #0x4  0100
    #0x2  0010
    #0x1  0001

    def __init__(self, inputString, version, phaseDiff=0 ):
        self.inputString = inputString
        self.version     = version
        self.phaseDiff   = phaseDiff
        #decode the words
        self.words = struct.unpack( '<3h', inputString )

        #the data packet should be +, -, +
        pattern = [v<0 for v in self.words]
        if not pattern == [False, True, False]:
            raise Exception( "Malformed data packet doesn't follow bit pattern" )
    
        self.decode()
    

    def decode( self ):
        """
        Yeah, this is just a mapping between version numbers, and decode 
        implementations.
        """
        if self.version == 12 or self.version==10:
            self.decode_12()

    def decode_12( self ):
        samplePeriod = 1e9/( 25000000 + self.phaseDiff )    #in ns
        windowLength = 80000    #80us

        self.aboveThresh = (self.words[0] >> 11) | ( (self.words[2]&0xFF00)>>4 )
        self.ticks       = (self.words[0] & 0x07FF)  #called nano by WR
        self.window      = (self.words[1] & 0x3FFF)  #called micro by WR
        self.maxData     = (self.words[2] & 0x00FF)
        
        #use the window number and ticks to get the actual time of this event
        #accurate to 1 ns
        self.nano        = self.window*windowLength + int( self.ticks*samplePeriod )
        #convert maxData to power in dBm
        self.power       = 0.488*self.maxData -111.0