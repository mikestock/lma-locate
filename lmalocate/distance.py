
import numpy as np
import math
import warnings

###
#TODO - change to relative imports
from constants import *
try:
    import cdistance
    Cython = True
except:
    warnings.warn( 'cDistance library could not be imported, is it compiled?')
    Cython = True

"""
The distance library provides a bunch of wrappers around the cdistance library
The overhead of the wrapper on execusion time is around 150ns per call 
(on the test Ryzen 3700 machine).  For some distance methods, this overhead is
more substantial than others
"""

def vincenty( geodesic1, geodesic2 ):
    """
    This is a wrapper around the cython vincenty implementation that 
    takes geodesics as input cause it's easier
    """
    lt1,ln1,z1 = geodesic1
    lt2,ln2,z2 = geodesic2
    if Cython:
        return cdistance.vincenty( lt1, ln1, lt2, ln2)
    else:
        return pyVincenty( lt1, ln1, lt2, ln2)

def euclidean( cartesian1, cartesian2 ):
    """
    Calculates the euclidean distance between two cartesian points
    This is as simple as it seems
    """
    x1,y1,z1 = cartesian1
    x2,y2,z2 = cartesian2
    if Cython:
        return cdistance.euclidean( x1,y1,z1,x2,y2,z2 )
    else:
        return math.sqrt( (x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2 )

def pyVincenty( lt1, ln1, lt2, ln2 ):
    """
    Adaptation of the Vincenty algorithm implementation by Maurycy
    https://github.com/maurycyp/vincenty
    I've largely just ripped out the conversion to km/miles, and 
    moved the whole thing over to Cython for improved speed

    Algorithm tested accurate against other implementations, and 
    only a few factors slower than the (much simpler) spherical 
    approximation

    input:  floats for lat1, lon1, lat2, lon2
    output: distances along the surface of the Earth 
            between (lat1,lon1) and (lat2,lon2) in meters
    
    This is the same as the vincenty function in cdistance, but slower
    """

    # short-circuit coincident points
    if lt1==lt2 and ln1==ln2:
        return 0.0

    MAX_ITERATIONS = 200
    CONVERGENCE_THRESHOLD = 1e-12  # .000,000,000,001

    lat1 = lt1*pi/180
    lat2 = lt2*pi/180
    lon1 = ln1*pi/180
    lon2 = ln2*pi/180 

    #interesting that this isn't a 2-term arctan here
    U1 = math.atan((1 - Eflattening) * math.tan(lat1))
    U2 = math.atan((1 - Eflattening) * math.tan(lat2))
    L = lon2-lon1
    Lambda = L


    sinU1 = math.sin(U1)
    cosU1 = math.cos(U1)
    sinU2 = math.sin(U2)
    cosU2 = math.cos(U2)

    for iteration in range(MAX_ITERATIONS):
        sinLambda = math.sin(Lambda)
        cosLambda = math.cos(Lambda)
        sinSigma = math.sqrt((cosU2 * sinLambda) ** 2 +
                             (cosU1 * sinU2 - sinU1 * cosU2 * cosLambda) ** 2)
        if sinSigma == 0:
            return 0.0  # coincident points
        cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosLambda
        sigma = math.atan2(sinSigma, cosSigma)
        sinAlpha = cosU1 * cosU2 * sinLambda / sinSigma
        cosSqAlpha = 1 - sinAlpha ** 2
        if cosSqAlpha == 0:
            cos2SigmaM = 0
        else:
            cos2SigmaM = cosSigma - 2 * sinU1 * sinU2 / cosSqAlpha

        C = Eflattening / 16 * cosSqAlpha * (4 + Eflattening * (4 - 3 * cosSqAlpha))
        LambdaPrev = Lambda
        Lambda = L + (1 - C) * Eflattening * sinAlpha * (sigma + C * sinSigma *
                                               (cos2SigmaM + C * cosSigma *
                                                (-1 + 2 * cos2SigmaM ** 2)))
        if abs(Lambda - LambdaPrev) < CONVERGENCE_THRESHOLD:
            break  # successful convergence
    else:
        return -1.0  # failure to converge


    uSq = cosSqAlpha * (Requa ** 2 - Rpole ** 2) / (Rpole ** 2)
    A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)))
    B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)))
    deltaSigma = B * sinSigma * (cos2SigmaM + B / 4 * (cosSigma *
                 (-1 + 2 * cos2SigmaM ** 2) - B / 6 * cos2SigmaM *
                 (-3 + 4 * sinSigma ** 2) * (-3 + 4 * cos2SigmaM ** 2)))
    s = Rpole * A * (sigma - deltaSigma)

    return s
