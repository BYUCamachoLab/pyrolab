# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Analysis
--------

Module for analyzing data from instruments included in PyroLab.
"""

import numpy as np
from scipy.signal import find_peaks


class WavelengthAnalyzer:
    """
    Uses a trigger signal to convert datasets from time-domain to wavelength.
    """
    def __init__(self, sample_rate, trigger_data, wavelength_log):
        self.sample_rate = sample_rate
        self.wavelength_log = wavelength_log
        self.__analyze_trigger(trigger_data)

    def __analyze_trigger(self, trigger_data):
        self.peaks, _ = find_peaks(trigger_data, height = 3, distance = 15)

    def num_peaks(self):
        return len(self.peaks)

    def process_data(self, raw_data):
        deviceData = raw_data[self.peaks[0]:self.peaks[-1]]
        #Time relative to the first collected data point.
        deviceTime = np.arange(len(deviceData)) / self.sample_rate

        modPeaks = self.peaks - self.peaks[0] #Make relative to the first point.
        modTime = modPeaks / self.sample_rate

        print("Peaks, Time, Wavelength", len(modPeaks), len(modTime), len(self.wavelength_log))
        #print(self.wavelength_log)


        fit = np.polyfit(modTime, self.wavelength_log, 2) #Least-squares fit.
        mapping = np.poly1d(fit) #Create function mapping time to wavelength.
        deviceWavelength = mapping(deviceTime) #Get wavelengths at given times.
        channelData = {
            "wavelengths": deviceWavelength,
            "data": deviceData,
            "wavelengthHash": hash(tuple(deviceWavelength)),
            "dataHash": hash(tuple(deviceData))
        }
        return channelData
        