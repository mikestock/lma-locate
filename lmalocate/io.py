#!/usr/bin/python
#
"""io
Reads and writes various LMA data formats
Support inlcudes:
In:
  raw lma v8 (80us)
  raw lma v9 (10us)
"""

import struct
import os
import sys
import time

class RawLMA:

    def __init__ (self, inputPath ):
        """
        inputPath = path to lma data file
        """

        self.inputPath = inputPath
        if os.path.exists( self.inputPath ):
            self.inputFile = open( self.inputPath, 'r' )
        else:
            raise Exception( 'RawLMA.__init__: inputPath does not exist: %s'%self.inputPath )
    
    def find_status( self ):
        pass
