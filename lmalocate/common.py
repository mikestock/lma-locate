import os, sys, time, warnings
import numpy as np

#local imports, these will have to be updated later
import distance
from constants import *

def latlonalt2xyz( lat,lon,alt ):
    #https://doi.org/10.1016/j.cageo.2019.104308
    #accuracy of calculation method tested against distance.distance3d, 
    #less than 0.5 meters of error across test of 10000 random distances < 200km 
    #around the globe.  Differences may be related to distance3d adding curvature, or being approximate

    #converting from lat/lon to xyz is easy
    lat *= np.pi/180
    lon *= np.pi/180
    #this is the denominator for the curvature N in the source above
    denom = np.sqrt( Requa**2 * np.cos(lat)**2 + Rpole**2 * np.sin(lat)**2 )

    x = (Requa**2/denom+alt) * np.cos( lat ) * np.cos( lon )
    y = (Requa**2/denom+alt) * np.cos( lat ) * np.sin( lon )
    z = (Rpole**2/denom+alt) * np.sin( lat )

    return x,y,z

def xyz2latlonalt( x,y,z ):
    #converting from cartesian to xyz is not so easy, 
    #this is going to require some approximations

    #longitude is easy, since it's not affected by earth flattening
    lon = np.arctan2( y,x )
    #according to source, this should be 
    #             2*np.arctan2( y, x+R) )
    #or np.pi/2 - 2*np.arctan2( x, y+R) )
    #depending on quadrant.  Numerical tests show no difference

    R = np.sqrt( x**2 + y**2 )

    #this is the initial guess for lat
    lat = np.arctan2( z, R )
    lat1 = 0

    #this algorithm is pulled from https://celestrak.com/columns/v02n03/
    #it seems to work, and converges quickly
    e2 = 2*Eflattening-Eflattening**2
    while abs(lat1-lat) > 1e-6:
        lat1 = lat
        C = (1-e2*np.sin(lat)**2) **-0.5  #not clear that the second term here is important
        lat  = np.arctan2( z + Requa*C*e2 * np.sin(lat1), R)

    #then apparently we can get the altitude directly
    alt = R/np.cos( lat ) - Requa*C

    return ( lat*180/np.pi, lon*180/np.pi, alt )


