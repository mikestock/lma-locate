#!/usr/bin/python
#
"""
Name TBD
Takes input data, phases together, and searches for initial-guesses in vicinity of phase center
"""

import os, sys, time, warnings
import numpy as np
#TODO - change to relative imports
from common import *
from constants import *
import raw_io

###
# Propagation Models
def euclidean_propagation( ob1, ob2 ):
    """
    Calculates the expected light propagation time difference 
    in nanoseconds between two objects, using their cartesian 
    locations
    """
    D = distance.euclidean( ob1.cartesian, ob2.cartesian )
    return D/Cns

class Phasor( ):

    def __init__( self, frames, locFile=None, propagationModel=euclidean_propagation, cartesian=None, geodetic=None, windowLength=80000, minSensors=5):
        """
        center -    is the phase center of the phasor, 
                    in geodetic or cartesian depending on propagationModel
        frames -    dict of LMAFrames of data
        """
        self.cartesian = cartesian
        self.geodetic  = geodetic
        self.frames    = frames
        if locFile == None:
            self.loc = raw_io.LocFile()
        else:
            self.loc = locFile

        #the propagation model calculates the expected arrival time of a signal at a sensor
        self.propagationModel = propagationModel

        #the windowLength sets how tightly the LMA raw peak times need to agree with the 
        #phase center.  This should relate to the LMA decimation used for the observation
        #specified in nano-seconds
        #common values are 10us, 80us, and 400us depending on LMA mode used
        self.windowLength = windowLength

        #the minSensors sets the minimum number of LMA sensors that need to agree on an 
        #initial guess before an initial guess is made.  
        #usually this should not be changed from 5
        self.minSensors = minSensors
    
        self.set_sensor_locations()

        self.phase_raw_data()

        self.find_initial_guesses()
    
    def set_sensor_locations( self ):
        """
        set_sensor_locations

        Looks at the LMA raw data, and the loc file to determine 
        where each sensor should be.  Hopefully they agree with 
        eachother
        """

        self.sensorIds = []
        for sensorId in self.frames:
            #add this ID to a sorted list for use later
            self.sensorIds.append( sensorId )
            #we may have information about this sensor from loc file
            if sensorId in self.loc.sensors:
                #we do have it, but we should test that it agrees
                D = distance.vincenty( self.loc.sensors[sensorId].geodetic, self.frames[sensorId].geodetic )
                if D > 10:
                    warnings.warn( 'Phasor.set_sensor_locations: sensor %s has different location in loc and raw files'%sensorId )
                #otherwise do nothing
            else:
                #we don't have this station, create station object
                frame = self.frames[sensorId]
                station = raw_io.Station( id=frame.id, geodetic=frame.geodetic, cartesian=frame.cartesian, delay=0)
                self.loc.add( station )

    def phase_raw_data( self ):
        """
        phase_raw_data

        Calculates delay between sensors and phasor center
        Applies these delays to the raw data, and adds all data into sorted array
        """

        self.sortedPeaks = np.empty( [0,4], dtype='i' )

        for i in range( len( self.sensorIds) ):
            id = self.sensorIds[i]
            #calculate the propagation time
            dt = self.propagationModel( self, self.frames[id] )

            #extend the sortedPeaks array
            N = len( self.sortedPeaks )
            M = len( self.frames[id].nano )
            self.sortedPeaks.resize( [N+M,4] )
            #source time
            self.sortedPeaks[N:,0] = self.frames[id].nano-dt
            #sensor ID - encode as int for easier cython schenanegans 
            self.sortedPeaks[N:,1] = ord( id )
            #arrival time
            self.sortedPeaks[N:,2] = self.frames[id].nano
            #power
            self.sortedPeaks[N:,3] = self.frames[id].power.astype('i')
        
        #there should be a better way to do this in-place, but for now this will work
        i = self.sortedPeaks[:,0].argsort()
        self.sortedPeaks = self.sortedPeaks[i]

    def find_initial_guesses(self):
        """
        find_initial_guesses

        loops over sorted array looking for possible locations
        """
        self.guesses = []
        lastGuess = 0
        iGuess = 0
        while iGuess < len(self.sortedPeaks)-self.minSensors :
            n = 1
            while self.sortedPeaks[iGuess+n,0]-self.sortedPeaks[iGuess,0] < self.windowLength:
                n += 1
                if iGuess+n >= len( self.sortedPeaks ):
                    #we're trying to walk off the end of the array
                    break
            if n > self.minSensors and iGuess+n > lastGuess:
                #count sensors
                sensors = set()
                guess = np.arange( iGuess, iGuess+n )
                for i in guess:
                    sensors.add( self.sortedPeaks[i,1] )
                if len(sensors) > self.minSensors:
                    self.guesses.append( guess )
                    lastGuess = iGuess+n
                    iGuess = iGuess+1
                else:
                    iGuess += 1
            else:
                iGuess += 1

class Solution():
    def __init__(self, peaks, nano=0, loc=None, propagationModel=None, geodetic=None, cartesian=None, phasor=None ):
        self.peaks     = peaks
        self.nano      = nano
        if phasor != None:
            #we can construct stuff from the parent phasor
            self.parentPhasor = phasor
            self.loc          = phasor.loc
            self.propagationModel = phasor.propagationModel
            self.cartesian    = phasor.cartesian
            self.geodetic     = phasor.geodetic
        else:
            #otherwise everything has to be constructed from individual arguments
            self.loc       = loc
            self.propagationModel = propagationModel
            self.geodetic  = geodetic
            self.cartesian = cartesian

        self.select_peaks()
        self.update()

    def update(self):
        """
        calculate various helper paramters, like the resilual, and 'quality'
        eventually this will probably do some work to make sure there is a geodetic location
        """

        self.resid   = self.calc_residual() 
        # self.quality = len(self.selectedPeaks)
        self.quality = self.calc_quality()

    def calc_residual( self, target=None ):
        """
        the target here is the location you're testing.  to use the propagation model right 
        now that's supposed to be an object with cartesian or geodetic attributes
        which sounds a lot like a 'Station' object
        """
        #if we're not passed a target, calculate the residual for where 
        #we think the solution is now.  
        if target == None: target = self

        #loop over peaks and apply the propagationModel to each
        resid = []
        resid = np.zeros( len( self.selectedPeaks) )
        i = 0
        for peak in self.selectedPeaks:
            #ugh, I need to convert the numerical id to a ascii id for this
            id = chr( peak[1] )
            dt = peak[2] - self.propagationModel( target, self.loc.sensors[id] ) - self.nano
            resid[i] = dt
            i += 1
        
        return resid
    
    def calc_quality( self ):
        """
        used mostly for sorting, this quality metric should not be used for filtering
        """
        #get the 5th highest residual.  
        if len(self.resid) < 5:
            #that's a problem actually
            r5 = abs(self.resid).max() * 2
        else:
            r5 = sorted(abs(self.resid))[4]
        
        return len( self.selectedPeaks ) / r5 * RmsTiming
    

    def select_peaks(self, nearest=False):
        #we always include the first peak
        selectedPeaks = [ self.peaks[0] ]
        selectedSensors = {self.peaks[0][1]}
        for i in range( 1, len( self.peaks) ):
            #use each sensor once
            if self.peaks[i][1] in selectedSensors: continue
            #find 'best' peak for this sensor
            bestPeak = self.peaks[i]
            for j in range( i+1, len( self.peaks) ):
                #not the same sensor
                if self.peaks[j][1] != bestPeak[1]: continue
                if self.peaks[j][3] > bestPeak[3]:
                    bestPeak = self.peaks[j]
            
            #we've found the best peak, might be the same one we started with
            #add it to the list
            selectedPeaks.append( bestPeak )
            selectedSensors.add( bestPeak[1] )  #this is a set, so we don't use 2 of the same sensor
        self.selectedPeaks = np.array( selectedPeaks )

    def __lt__( self, other ):
        """
        we want the default sort order to have the 'best' solutions at the beginning of the list
        so, we're reversing the sort order here
        """
        return self.quality > other.quality
    
    def __repr__( self ):
        #TODO - finish this method
        return 'Solution: %8.6f'%(self.quality)

