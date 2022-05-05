"""
Fundamental constants.  I don't expect these guys to change anytime soon
"""

###
# The Speed of Light in handy units
Cms = 299792.458   #speed of light, m/ms
Cus = 299.792458   #speed of light, m/us
Cns = 0.299792458  #speed of light, m/ns

###
# Earth Radius Constants
Re  = 6371000 #meters (mean Earth radius)
Rpole = 6356752.  #meters (polar Earth radius)
Requa = 6378137.  #meters (equatorial Earth radius)
Eflattening = 0.0033528599338647    #used in some eliptical calculations, (1-f) = Requa/Rpole
Earc  = 111195.  #meters/degree (Earth mean arclength)

###
# network parameters
RmsTiming = 70  #nanoseconds expected rms error in timeing