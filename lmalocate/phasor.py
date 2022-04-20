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

class Phasor( ):

    def __init__( self, center, frames, locFile=None, propagationModel=None, windowLength=80000, minSensors=5):
        """
        center -    is the phase center of the phasor, 
                    in geodesic or cartesian depending on propagationModel
        frames -    dict of LMAFrames of data
        """
        self.center  = center
        self.frames  = frames
        self.locFile = locFile

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

        for sensorKey in self.frames:


    def phase_raw_data( self ):
        """
        phase_raw_data

        Calculates delay between sensors and phasor center
        Applies these delays to the raw data, and adds all data into sorted array
        """
    
    def find_initial_guesses(self):
        """
        find_initial_guesses

        loops over sorted array looking for possible locations
        """