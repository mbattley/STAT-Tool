#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 19 13:26:10 2018

This code investigates the reverse evolution of clusters by running their 
current proper motions back in time by the approximate age of the system.

@author: Matthew Battley
"""

import astropy.table as tab
import numpy as np
import matplotlib.pyplot as plt
import pylab
import timeit
from astropy.coordinates import SkyCoord
from math import sin, cos


start = timeit.default_timer()

def uvw(ra, dec, d, pmra, pmdec, rv):
    """
    Calculates galactic UVW velocities given ra, dec, distance, pmra, pmdec and RV
    
        PARAMETER - UNIT - DESCRIPTION
        ______________________________
    Inputs:
        ra        - deg    - Right Ascension
        dec       - deg    - Declination
        d         - pc     - Distance
        pmra      - mas/yr - Proper motion, Right Ascension
        pmdec     - mas/yr - Proper motion, Declination
        rv        - km/s   - Radial Velocity
    Outputs:
        U         - km/s   - Cartesian Galactic Velocity in X direction
                                Positive toward Galactic center
        V         - km/s   - Cartesian Galactic Velocity in Y direction
                                Positive in direction of Galactic rotation
        W         - km/s   - Cartesian Galactic Velocity in Z direction
                                Positive toward North Galactic Pole
    """
    
    # Initialise conversion constants
    k = 4.74047 # km/s equivalent of 1AU/yr
    A = [[0.0548755604,   0.4941094279, -0.8676661490],
         [0.8734370902, - 0.4448296300, -0.1980763734],
         [0.483850155,    0.7469822445, +0.4559837762]]
    
    # Sets all parameters as arrays in case they were entered as lists
    ra = np.array(ra)
    dec = np.array(dec)
    d = np.array(d)
    pmra = np.array(pmra)
    pmdec = np.array(pmdec)
    rv = np.array(rv)
    
    # Precalculates trigonometric values
    cos_ra  = np.array([cos(i*np.pi/180) for i in ra])
    sin_ra  = np.array([sin(i*np.pi/180) for i in ra])
    cos_dec = np.array([cos(i*np.pi/180) for i in dec])
    sin_dec = np.array([sin(i*np.pi/180) for i in dec])
    
    # Set up velocities
    plx = 1000.0*1/d #parallax in mas
    vec1 = rv
    vec2 = k*pmra/plx
    vec3 = k*pmra/plx
    
    # Calculate cartesian UVW velocities
    u = ( A[0][0]*cos_ra*cos_dec + A[0][1]*sin_ra*cos_dec + A[0][2]*sin_dec)*vec1 + \
        (-A[0][0]*sin_ra         + A[0][1]*cos_ra                          )*vec2 + \
        (-A[0][0]*cos_ra*sin_dec - A[0][1]*sin_ra*sin_dec + A[0][2]*cos_dec)*vec3
    v = ( A[1][0]*cos_ra*cos_dec + A[1][1]*sin_ra*cos_dec + A[1][2]*sin_dec)*vec1 + \
        (-A[1][0]*sin_ra         + A[1][1]*cos_ra                          )*vec2 + \
        (-A[1][0]*cos_ra*sin_dec - A[1][1]*sin_ra*sin_dec + A[1][2]*cos_dec)*vec3
    w = ( A[2][0]*cos_ra*cos_dec + A[2][1]*sin_ra*cos_dec + A[2][2]*sin_dec)*vec1 + \
        (-A[2][0]*sin_ra         + A[2][1]*cos_ra                          )*vec2 + \
        (-A[2][0]*cos_ra*sin_dec - A[2][1]*sin_ra*sin_dec + A[2][2]*cos_dec)*vec3
    u = -u # Reversing U so that it is +ve towards Galactic center
    
    return u,v,w

def old_position_angle(current_ra, current_dec, pmra, pmdec, age):
    """
    Calculates the old ra/dec positions of stars given their current positions,
    velcoities and approximate ages
    
        PARAMETER   - UNIT
        __________________
    Inputs:
        current_ra  - deg
        current_dec - deg
        pmra        - mas/yr = deg/Myr
        pmdec       - mas/yr = deg/Myr
        age         - Myr
    Outputs:
        old_ra      - deg
        old_dec     - deg
    
    """
    #nb units = mas/yr * Myr = deg/Myr * Myr = deg 
    old_ra = current_ra - pmra*age 
    old_dec = current_dec - pmdec*age
    
    return old_ra, old_dec

# Read data from table
Table = tab.Table
#hipparcos_data = Table.read('Hipparcos_OB2_de_Zeeuw_1999.vot')
hipparcos_data = Table.read('OB2_Gaia_Zeeuw_Match_dist')

# Change from unrecognisable unit names in file
hipparcos_data['pmra'].unit = 'mas/yr'
hipparcos_data['pmdec'].unit = 'mas/yr'
hipparcos_data['ra'].unit = 'deg'
hipparcos_data['dec'].unit = 'deg'

# Assembles age matrix (in this case, quite approximate, broken only into Sco_Cen groups)
hipparcos_data['age'] = np.array(['None']*len(hipparcos_data['ra']))
US_age = 11 # Myr
UCL_age = 16 # Myr
LCC_age = 17 #Myr
#US_age = 10 # Myr
#UCL_age = 10 # Myr
#LCC_age = 10 #Myr


for i, data in enumerate(hipparcos_data['OBAss']):
    if data == 'A':
        hipparcos_data['age'][i] = US_age
    elif data == 'B':
        hipparcos_data['age'][i] = UCL_age
    else:
        hipparcos_data['age'][i] = LCC_age

ages = [float(i) for i in hipparcos_data['age']] # (Myr)

# Input sky coordinates for all stars
c_icrs_hipparcos = SkyCoord(ra = hipparcos_data['ra'], dec = hipparcos_data['dec'], pm_ra_cosdec = hipparcos_data['pmra'], pm_dec = hipparcos_data['pmdec'])

# Convert star coordinates to Galactic frame
c_galactic_hipparcos = c_icrs_hipparcos.galactic
#print(c_galactic_hipparcos)

# Add equivalent galactic coordinates back into data
hipparcos_data['l'] = c_galactic_hipparcos.l
hipparcos_data['b'] = c_galactic_hipparcos.b
hipparcos_data['pm_l_cosb'] = c_galactic_hipparcos.pm_l_cosb
hipparcos_data['pm_b'] = c_galactic_hipparcos.pm_b

# Calculates approximate initial distribution of OB2 members given approximate association age
original_l, original_b = old_position_angle(hipparcos_data['l'], hipparcos_data['b'], hipparcos_data['pm_l_cosb'],hipparcos_data['pm_b'],ages)

# Compensates for going around multiple times
for i, data in enumerate(original_l):
    if data >= 360:
        original_l[i] = data - 360*(data//360)
#    if data < 0:
#        original_l[i] = data + 360*(data//360)
#
#for i, data in enumerate(original_dec):
#    if data > 90:
#        original_dec[i] = data - 180*(1+data//180)
#    if data < -90:
#        original_dec[i] = data + 180*(1+data//180)

# Plots positions at current time
plt.figure()
plt.scatter(hipparcos_data['l'], hipparcos_data['b'], 1)
plt.title('Position of confirmed OB2 Association members at current time')
plt.xlabel('l (deg)')
plt.ylabel('b (deg)')

# Plots positions of association stars near formation
plt.figure()
plt.scatter(original_l, original_b, 2)
plt.title('Position of confirmed OB2 Association members near splitting time \n Age ={0} Myr'.format(hipparcos_data['age'][0]))
plt.xlabel('l (deg)')
plt.ylabel('b (deg)')
#plt.xlim([0,360])
#plt.ylim([-90,90])

# Plot figure with arrows for velocities
plt.figure()
pylab.quiver(hipparcos_data['l'], hipparcos_data['b'], hipparcos_data['pm_l_cosb'], hipparcos_data['pm_b'], angles = 'uv', scale_units='xy', scale = 8)
plt.title('Position and Velocities of confirmed OB2 Association members at current time')
plt.xlabel('l (deg)')
plt.ylabel('b (deg)')

#########################################################################################################################################################################
# Now in Galactic XYZ UVW space:

# Calculate  current XYZ Galactic positions (X = d*cos(b)*cos(l); Y = d*cos(b)*sin(l); Z = d*sin(b) --- (pc)
x_g = np.array([hipparcos_data['rest'][i] * cos(hipparcos_data['b'][i]*np.pi/180) * cos(hipparcos_data['l'][i]*np.pi/180) for i,d1 in enumerate(hipparcos_data['b'])]) 
y_g = np.array([hipparcos_data['rest'][i] * cos(hipparcos_data['b'][i]*np.pi/180) * sin(hipparcos_data['l'][i]*np.pi/180) for i,d1 in enumerate(hipparcos_data['b'])]) 
z_g = np.array([hipparcos_data['rest'][i] * sin(hipparcos_data['b'][i]*np.pi/180) for i,d1 in enumerate(hipparcos_data['b'])])

# Calculate UVW galactic velocities --- (km/s)
u_g, v_g, w_g = uvw(ra = hipparcos_data['ra'], dec = hipparcos_data['dec'], d = hipparcos_data['rest'], pmra = hipparcos_data['pmra'], pmdec = hipparcos_data['pmdec'], rv = hipparcos_data['radial_velocity'])

# Calculate old XYZ positions
vel_conv = 1.02269 #((pc/Myr)/(km/s)) --- conversion factor to change velocity units from km/s to pc/Myr 
x_g_old = x_g - u_g*vel_conv*ages
y_g_old = y_g - v_g*vel_conv*ages
z_g_old = z_g - w_g*vel_conv*ages

# Plots XYZ positions at current time
plt.figure()
plt.scatter(x_g, y_g, 1)
plt.title('Galactic XY Position of confirmed OB2 Association members \n Current time')
plt.xlabel('X (pc)')
plt.ylabel('Y (pc)')

# Plots positions of association at 'age' of association
plt.figure()
plt.scatter(x_g_old, y_g_old, 1)
plt.title('Galactic XY Position of confirmed OB2 Association members \n {0} Myr ago'.format(hipparcos_data['age'][0]))
plt.xlabel('X (pc)')
plt.ylabel('Y (pc)')

# Plot figure with arrows for velocities
plt.figure()
pylab.quiver(x_g, y_g, u_g, v_g, angles = 'uv', scale_units='xy', scale = 3)
plt.title('Galactic XY Position of confirmed OB2 Association members, with overplotted UV velocities \n Current time')
plt.xlabel('X (pc)')
plt.ylabel('Y (pc)')

stop = timeit.default_timer()

print('Time: ',stop - start)