from libc.math cimport cos, sin, sqrt, pi, atan2, atan, tan, asin

def euclidean( double x1, double y1, double z1, double x2, double y2, double z2 ):
    """
    Calculates simple straight line distance between 2 locations in cartesian coords
    This is very simple
    """

    cdef double D

    D  = (x1-x2)**2
    D += (y1-y2)**2
    D += (z1-z2)**2
    return sqrt( D )

def pythagorean( double lt1, double ln1, double lt2, double ln2 ):
    """
    Implementation of the approximate geodesic distance on an 
    oblate spheroid assuming a flat Earth. 
    Approximation uses a model to estimate the conversion from 
    degrees to km, and then gets distance using a Cartesian 
    distance
    Accuracy is reasonable out to around 100km
    
    input:  floats for lat1, lon1, lat2, lon2
    output: distances along the surface of the Earth 
            between (lat1,lon1) and (lat2,lon2) in meters
    """

    cdef double lat1, lat2, lon1, lon2, F, KPD_lat, KPD_lon,A,B,rng
    #copy and convert to radians
    lat1 = lt1*pi/180
    lat2 = lt2*pi/180
    lon1 = ln1*pi/180
    lon2 = ln2*pi/180    

    F = (lat1+lat2)/2

    KPD_lat = 111.13209-0.56605*cos(2*F)+0.0012*cos(4*F)
    KPD_lon = 111.41513*cos(F)-0.09455*cos(3*F)+0.00012*cos(5*F)

    A = (KPD_lon*(lon1-lon2)*180/pi)
    B = (KPD_lat*(lat1-lat2)*180/pi)

    rng = sqrt( A*A + B*B )*1000
    return rng

def oblate( double lt1, double ln1, double lt2, double ln2 ): 
    """
    Implementation of the approximate geodesic distance on an 
    oblate spheroid.  I don't remember where I found this 
    implementation, but I did not derive it.
    Accuracy is quite good out to several thousand km
    Not suitible for very very small distances
    
    input:  floats for lat1, lon1, lat2, lon2
    output: distances along the surface of the Earth 
            between (lat1,lon1) and (lat2,lon2) in meters
    """

    cdef double lat1, lat2, lon1, lon2, F, G, L, sing, cosl, cosf, sinl, sinf, cosg, S, C, W, R, H1, H2, D, R_EARTH_EQUA, EARTH_FLATTENING

    # short-circuit coincident points
    if lt1==lt2 and ln1==ln2:
        return 0.0

    R_EARTH_EQUA = 6378137.0
    EARTH_FLATTENING = 0.0033528599338647

    #copy and convert to radians
    lat1 = lt1*pi/180
    lat2 = lt2*pi/180
    lon1 = ln1*pi/180
    lon2 = ln2*pi/180  

    F = (lat1+lat2)/2
    G = (lat1-lat2)/2
    L = (lon1-lon2)/2

    #trig functions take computation time, calculate them all at once, and only once
    sing = sin(G)
    cosl = cos(L)
    cosf = cos(F)
    sinl = sin(L)
    sinf = sin(F)
    cosg = cos(G)

    S = sing*sing*cosl*cosl + cosf*cosf*sinl*sinl
    C = cosg*cosg*cosl*cosl + sinf*sinf*sinl*sinl
    W = atan2(sqrt(S),sqrt(C))

    R = sqrt((S*C))/W
    H1 = (3 * R - 1.0) / (2.0 * C)
    H2 = (3 * R + 1.0) / (2.0 * S)
    D = 2 * W * R_EARTH_EQUA
    return (D * (1 + EARTH_FLATTENING * H1 * sinf*sinf*cosg*cosg - EARTH_FLATTENING*H2*cosf*cosf*sing*sing))

def spherical( double lt1, double ln1, double lt2, double ln2 ):
    """
    Implementation of the Haversine formula to calculate the 
    distance between two points on Earth, assuming a Spherical 
    Earth.

    input:  floats for lat1, lon1, lat2, lon2
    output: distances along the surface of the Earth 
            between (lat1,lon1) and (lat2,lon2) in meters
    """
    cdef double lat1, lat2, lon1, lon2, dlat, dlon, a, R_EARTH

    R_EARTH      = 6371000

    lat1 = lt1*pi/180
    lat2 = lt2*pi/180
    lon1 = ln1*pi/180
    lon2 = ln2*pi/180 

    dlat = lat1-lat2
    dlon = lon1-lon2
    
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return R_EARTH * 2 * atan2( sqrt(a), sqrt( 1-a ) )

def vincenty( double lt1, double ln1, double lt2, double ln2 ):
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
    """
    cdef double lat1, lat2, lon1, lon2, U1, U2, L, C, Lambda, LambdaPrev, sinU1, cosU1, sinU2, cosU2, 
    cdef double sinLambda, cosLambda, sinSigma, cosSigma, sigma, sinAlpha, cosSqAlpha, cos2SigmaM
    cdef double R_EARTH_EQUA, EARTH_FLATTENING,R_EARTH_POLE
    cdef int MAX_ITERATIONS

    # short-circuit coincident points
    if lt1==lt2 and ln1==ln2:
        return 0.0

    R_EARTH_EQUA = 6378137.0
    R_EARTH_POLE = 6356752.0
    EARTH_FLATTENING = 0.0033528599338647
    MAX_ITERATIONS = 200
    CONVERGENCE_THRESHOLD = 1e-12  # .000,000,000,001

    lat1 = lt1*pi/180
    lat2 = lt2*pi/180
    lon1 = ln1*pi/180
    lon2 = ln2*pi/180 

    #interesting that this isn't a 2-term arctan here
    U1 = atan((1 - EARTH_FLATTENING) * tan(lat1))
    U2 = atan((1 - EARTH_FLATTENING) * tan(lat2))
    L = lon2-lon1
    Lambda = L


    sinU1 = sin(U1)
    cosU1 = cos(U1)
    sinU2 = sin(U2)
    cosU2 = cos(U2)

    for iteration in range(MAX_ITERATIONS):
        sinLambda = sin(Lambda)
        cosLambda = cos(Lambda)
        sinSigma = sqrt((cosU2 * sinLambda) ** 2 +
                             (cosU1 * sinU2 - sinU1 * cosU2 * cosLambda) ** 2)
        if sinSigma == 0:
            return 0.0  # coincident points
        cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosLambda
        sigma = atan2(sinSigma, cosSigma)
        sinAlpha = cosU1 * cosU2 * sinLambda / sinSigma
        cosSqAlpha = 1 - sinAlpha ** 2
        if cosSqAlpha == 0:
            cos2SigmaM = 0
        else:
            cos2SigmaM = cosSigma - 2 * sinU1 * sinU2 / cosSqAlpha

        C = EARTH_FLATTENING / 16 * cosSqAlpha * (4 + EARTH_FLATTENING * (4 - 3 * cosSqAlpha))
        LambdaPrev = Lambda
        Lambda = L + (1 - C) * EARTH_FLATTENING * sinAlpha * (sigma + C * sinSigma *
                                               (cos2SigmaM + C * cosSigma *
                                                (-1 + 2 * cos2SigmaM ** 2)))
        if abs(Lambda - LambdaPrev) < CONVERGENCE_THRESHOLD:
            break  # successful convergence
    else:
        return -1.0  # failure to converge

    cdef double uSq, A, B, deltaSigma, s

    uSq = cosSqAlpha * (R_EARTH_EQUA ** 2 - R_EARTH_POLE ** 2) / (R_EARTH_POLE ** 2)
    A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)))
    B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)))
    deltaSigma = B * sinSigma * (cos2SigmaM + B / 4 * (cosSigma *
                 (-1 + 2 * cos2SigmaM ** 2) - B / 6 * cos2SigmaM *
                 (-3 + 4 * sinSigma ** 2) * (-3 + 4 * cos2SigmaM ** 2)))
    s = R_EARTH_POLE * A * (sigma - deltaSigma)

    return s

def distance3d( double D, double h ):
    """
    Applies a geometric correction for calculating slant distance 
    between two points separated by distance D along the surface 
    of the Earth and height h
    The correction assumes a spherical Earth, but the approximation 
    essentially cancels out, maintaining high accuracy results

    input:  Geodesic distance, and height above surface
    output: 3D distance in meters
    """
    cdef double R, tangentAngle, theta, R1, R2, s

    R_EARTH      = 6371000  #meters

    #calculate the tangent angle based on h
    R = sqrt( 2*R_EARTH*h + h*h )
    tangentAngle = asin( R/(R_EARTH+h) )

    if tangentAngle > D/R_EARTH:
        #we use law of cosines
        theta = D/R_EARTH
        R1 = R_EARTH
        R2 = R_EARTH+h
        return sqrt( R1*R1 + R2*R2 - 2*R1*R2*cos(theta) )
    else:
        #we use peicewise distance
        s = R_EARTH*tangentAngle
        return D-s+R