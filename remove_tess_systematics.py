#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 11:46:37 2019

Tidies tess data based on the removing systematics of each individual sector
Focusses in particular on cadences with overly large scatter, momentum dumps or
known instrumental anomalies

@author: mbattley
"""

from astropy.io import fits
import batman
import lightkurve
import pickle
import random
import scipy.fftpack
import numpy as np
import matplotlib.pyplot as plt
import astropy.units as u
import statsmodels.api as sm
from TESSselfflatten import TESSflatten
from astropy.timeseries import LombScargle
from lightkurve import search_lightcurvefile
from lc_download_methods import *
from statsmodels.nonparametric.kernel_regression import KernelReg
from scipy.signal import find_peaks
from astropy.timeseries import BoxLeastSquares
from wotan import flatten
from astropy.io import ascii
from astropy.table import Table
from scipy import interpolate

def bin(time, flux, binsize=15, method='mean'):
    """Bins a lightcurve in blocks of size `binsize`.
    n.b. based on the one from eleanor
    """
    available_methods = ['mean', 'median']
    if method not in available_methods:
        raise ValueError("method must be one of: {}".format(available_methods))
    methodf = np.__dict__['nan' + method]

    n_bins = len(flux) // binsize
    indexes = np.array_split(np.arange(len(time)), n_bins)
    binned_time = np.array([methodf(time[a]) for a in indexes])
    binned_flux = np.array([methodf(flux[a]) for a in indexes])

    return binned_time, binned_flux

def plot_quaternions(time, q_data, sector, camera=1, q=1):    
    plt.figure()
    plt.scatter(time, q_data, s=1, c='k')
    plt.title('Base Quaternion plot for Sector {} - Camera {} - Q{}'.format(sector, camera, q))
    plt.xlabel('Time - 2457000 [BTJD days]')
    plt.ylabel('Raw Q{} Quaternions'.format(q))

def plot_quaternions_2min(time, q_data, sector, camera=1, q=1):
    #Bin data
    binned_time, binned_q = bin(time,q_data, binsize=60)
    
    plt.figure()
    plt.scatter(binned_time, binned_q, s=1, c='k')
    plt.title('2min Quaternion plot for Sector {} - Camera {} - Q{}'.format(sector, camera, q))
    plt.xlabel('Time - 2457000 [BTJD days]')
    plt.ylabel('2min Q{} Quaternions'.format(q))
    
def plot_quaternions_30min(time, q_data, sector, camera=1, q=1):
    #Bin data
    binned_time, binned_q = bin(time,q_data, binsize=900)
    
    plt.figure()
    plt.scatter(binned_time, binned_q, s=1, c='k')
    plt.title('30min Quaternion plot for Sector {} - Camera {} - Q{}'.format(sector, camera, q))
    plt.xlabel('Time - 2457000 [BTJD days]')
    plt.ylabel('30min Q{} Quaternions'.format(q))
    print('Length of 30min data = {}'.format(len(binned_time)))
    
def view_quaternions(sector = 1, camera = 1, quaternion = 1):
    filename_list = [None,'tess2018331094053_sector01-quat.fits', 'tess2018330083923_sector02-quat.fits', 'tess2018344131939_sector03-quat.fits',
                     'tess2018344132117_sector04-quat.fits', 'tess2019024141334_sector05-quat.fits','tess2019050105252_sector06-quat.fits',
                     'tess2019050113148_sector07-quat.fits','tess2019060083045_sector08-quat.fits','tess2019093074938_sector09-quat.fits',
                     'tess2019136122405_sector10-quat.fits','tess2019140185400_sector11-quat.fits','tess2019170120618_sector12-quat.fits',
                     'tess2019207131829_sector13-quat.fits','tess2019227202023_sector14-quat.fits','tess2019255102657_sector15-quat.fits',
                     'tess2019280102352_sector16-quat.fits','tess2019307010433_sector17-quat.fits','tess2019331203517_sector18-quat.fits',
                     'tess2019357232015_sector19-quat.fits']
    
    input_filename = filename_list[sector]
    
    with fits.open(input_filename) as hdul:
        #hdul.info()
        #print(hdul['CAMERA1'].header)
        cam1_data = hdul['CAMERA{}'.format(camera)].data
        time = cam1_data.field('Time')
        cx_Qx = cam1_data.field('C{}_Q{}'.format(camera,quaternion))
    
    # Plot each individually
    plot_quaternions(time, cx_Qx, sector, camera, quaternion)
#    plot_quaternions_2min(time, cx_Qx, sector, camera, quaternion)
#    plot_quaternions_30min(time, cx_Qx, sector, camera, quaternion)
    
    ###########################################################################
#    # Plotting raw and 30min in one:
#    fig, axs = plt.subplots(2, 1, sharex=True)
#    fig.subplots_adjust(hspace=0)
#    
#    line1 = axs[0].scatter(time, cx_Qx, s=1, c='k')
#    #axs[0].set_ylabel('Raw Q1 Quaternions')
#    axs[0].set_ylim(-0.0006,0.0006)
#    axs[0].legend([line1],['Raw'], loc='upper right')
#    
#    binned_time, binned_q = bin(time,cx_Qx, binsize=900)
#    line2 = axs[1].scatter(binned_time, binned_q, s=1, c='g')
#    #axs[1].set_ylabel('30min Q1 Quaternions')
#    axs[1].set_ylim(-0.00005,0.00005)
#    axs[1].legend([line2],['30min'], loc='upper right')
#    
#    axs[1].set_xlabel('Time - 2457000 [BTJD days]')
#    fig.text(0.01, 0.5, 'Q1 Quaternions (arcsec)', va='center', rotation='vertical')
#    
#    plt.show()
    ###########################################################################
    
    # Generate mask based on those above 5sd
    sd_cx_Qx = np.std(cx_Qx)
    q_mask = np.abs(cx_Qx) < 5*sd_cx_Qx
    
    new_time = time[q_mask]
    new_q = cx_Qx[q_mask]
    
    plt.figure()
    plt.scatter(new_time, new_q, s=1, c='k')
    
    bad_times = time[~q_mask]
    rounded_bad_times = np.round(bad_times, decimals = 2)
    unique_bad_times = np.unique(rounded_bad_times)
    #with open('s{}_bad_times.pkl'.format(sector), 'wb') as f:
    #    pickle.dump(unique_bad_times, f, pickle.HIGHEST_PROTOCOL)
    
    return unique_bad_times

def clean_tess_lc(time, flux, flux_err, target_ID, sector, save_path):
    # Momentum Dump times:
    s1_mom_dumps = [1327.84, 1330.34, 1332.84, 1335.34, 1337.84, 1342.18, 1344.68, 1347.18, 1349.68, 1352.18]
    s2_mom_dumps = [1356.63, 1359.13, 1361.63, 1364.13, 1366.63, 1371.12, 1373.62, 1376.12, 1378.62, 1381.12]
    s3_mom_dumps = [1387.75, 1390.25, 1392.75, 1395.25, 1395.58, 1396.47, 1396.57, 1398.71, 1400.71, 1402.71, 1404.71, 1406.25, 1409.56, 1410.71]
    s4_mom_dumps = [1413.26, 1413.94, 1416.94, 1422.94, 1427.58, 1430.58, 1433.58, 1436.58]
    s5_mom_dumps = [1441.02, 1444.02, 1447.02, 1450.02, 1454.59, 1457.59, 1460.59, 1463.59]
    
    # Loads bad scattering epochs based on Quaternions 
#    unique_bad_times = view_quaternions(sector, camera = 1, quaternion = 1)
    with open('s1_bad_times.pkl', 'rb') as f:
        s1_bad_times = pickle.load(f)
    with open('s2_bad_times.pkl', 'rb') as f:
        s2_bad_times = pickle.load(f)
    with open('s3_bad_times.pkl', 'rb') as f:
        s3_bad_times = pickle.load(f)
    with open('s4_bad_times.pkl', 'rb') as f:
        s4_bad_times = pickle.load(f)
    with open('s5_bad_times.pkl', 'rb') as f:
        s5_bad_times = pickle.load(f)
    with open('s6_bad_times.pkl', 'rb') as f:
        s6_bad_times = pickle.load(f)
    with open('s7_bad_times.pkl', 'rb') as f:
        s7_bad_times = pickle.load(f)
    with open('s8_bad_times.pkl', 'rb') as f:
        s8_bad_times = pickle.load(f)
    with open('s9_bad_times.pkl', 'rb') as f:
        s9_bad_times = pickle.load(f)
    with open('s10_bad_times.pkl', 'rb') as f:
        s10_bad_times = pickle.load(f)
    with open('s11_bad_times.pkl', 'rb') as f:
        s11_bad_times = pickle.load(f)
    with open('s12_bad_times.pkl', 'rb') as f:
        s12_bad_times = pickle.load(f)
    with open('s13_bad_times.pkl', 'rb') as f:
        s13_bad_times = pickle.load(f)
    with open('s14_bad_times.pkl', 'rb') as f:
        s14_bad_times = pickle.load(f)
    with open('s15_bad_times.pkl', 'rb') as f:
        s15_bad_times = pickle.load(f)
    with open('s16_bad_times.pkl', 'rb') as f:
        s16_bad_times = pickle.load(f)
    with open('s17_bad_times.pkl', 'rb') as f:
        s17_bad_times = pickle.load(f)
    with open('s18_bad_times.pkl', 'rb') as f:
        s18_bad_times = pickle.load(f)
    with open('s19_bad_times.pkl', 'rb') as f:
        s19_bad_times = pickle.load(f)
    
    for_removal = [False]*len(time)
    
    if sector == 1:
        mom_dumps = s1_bad_times
#        for i in range(len(time)):
#            if time[i] > 1348 and time[i] < 1349.29:
#                for_removal[i] = True
    elif sector == 2:
        mom_dumps = s2_bad_times
    elif sector == 3:
        mom_dumps = s3_bad_times
        for i in range(len(time)):
            if time[i] < 1385.8966:
                for_removal[i] = True
            elif time[i] > 1406.2925:
                for_removal[i] = True
            elif time[i] > 1395.4800 and time[i] < 1396.6050:
                for_removal[i] = True
    elif sector == 4:
        mom_dumps = s4_bad_times
        for i in range(len(time)):
            if time[i] > 1418.53691 and time[i] < 1421.21168:
                for_removal[i] = True
    elif sector == 5:
        mom_dumps = s5_bad_times
    elif sector == 6:
        mom_dumps = s6_bad_times
    elif sector == 7:
        mom_dumps = s7_bad_times
    elif sector == 8:
        mom_dumps = s8_bad_times
    elif sector == 9:
        mom_dumps = s9_bad_times
    elif sector == 10:
        mom_dumps = s10_bad_times
    elif sector == 11:
        mom_dumps = s11_bad_times
    elif sector == 12:
        mom_dumps = s12_bad_times
    elif sector == 13:
        mom_dumps = s13_bad_times
    elif sector == 14:
        mom_dumps = s14_bad_times
    elif sector == 15:
        mom_dumps = s15_bad_times
#        if time[i] < 1711.45:
#            for_removal[i] = True
        for i in range(len(time)):
            if time[i] > 1737.3:
                for_removal[i] = True
    elif sector == 16:
        mom_dumps = s16_bad_times
    elif sector == 17:
        mom_dumps = s17_bad_times
    elif sector == 18:
        mom_dumps = s18_bad_times
        for i in range(len(time)):
            if time[i] < 1791.5:
                for_removal[i] = True
            if time[i] > 1813.48:
                for_removal[i] = True
    elif sector == 19:
        mom_dumps = s19_bad_times
    
    # Removing momentum dumps:
    for i in mom_dumps:
        for j in range(len(time)):
            if abs(time[j] - i) < 0.015:
                for_removal[j] = True
    
    for_removal = np.array(for_removal)
    
    clean_time = time[~for_removal]
    clean_flux = flux[~for_removal]
    clean_flux_err = flux_err[~for_removal]
    
#    plt.figure()
#    plt.scatter(clean_time, clean_flux, s=1, c='k')
#    plt.title('{} after removing poor TESS pointing epochs'.format(target_ID))
    
    return clean_time, clean_flux, clean_flux_err

#target_ID = 'HIP 1993'
#sector = 1
#save_path = '/Users/mbattley/Documents/PhD/TESS Systematics Removal/'
#
#lc_30min, filename = diff_image_lc_download(target_ID, sector, plot_lc = True, save_path = save_path, from_file = True)
#time = lc_30min.time
#flux = lc_30min.flux
#flux_err = lc_30min.flux_err
#
#clean_time, clean_flux, clean_flux_err = clean_tess_lc(time, flux, flux_err, target_ID, sector, save_path)
