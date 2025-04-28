# -*- coding: utf-8 -*-
#
# Copyright © Autogator Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see autogator/__init__.py for details)

"""
# Analysis

A series of convenience functions for processing raw data.
"""

from pathlib import Path
from typing import NamedTuple
import numpy as np
from scipy.signal import find_peaks

from pyrolab.drivers.scopes.rohdeschwarz import RTO
from pyrolab.api import locate_ns, Proxy


class AnalysisResult(NamedTuple):
    """
    A named tuple for storing analysis results.

    Attributes
    ----------
    wl : ndarray
        Wavelength values.
    data : ndarray
        Corresponding data values.
    """

    wl: np.ndarray
    data: np.ndarray

    @property
    def wavelength_hash(self) -> str:
        """The hash of the wavelength data."""
        return hash(self.wl)

    @property
    def data_hash(self) -> str:
        """The hash of the raw data."""
        return hash(self.data)


class WavelengthAnalyzer:
    """
    Uses a trigger signal to convert datasets from time-domain to wavelength.

    Correlates a trigger signal, typically output from a laser, to a dataset.
    The laser logs the current wavelength each time the trigger is high.
    The trigger signal is expected to be a single channel of data as acquired
    by a data acquisition device. The wavelength sweep rate may not be constant
    or linear in time. After receiving trigger data and the corresponding
    wavelengths, a curve is fit to the wavelength as a function of time.
    Wavelengths for the raw data is then calculated by sampling the curve at
    the same time points as the raw data.

    Parameters
    ----------
    sample_rate : float
        The sample rate of the acquired data. Sample rate of the trigger signal
        should be the same as the sample rate of the raw data.
    trigger_data : ndarray
        The collected trigger signal. A peak finding algorithm is used to
        correlate time points to the wavelength log.
    wavelength_log : ndarray
        Log of wavelengths for each time the trigger signal was high.
    """

    def __init__(
        self, sample_rate: float, trigger_data: np.ndarray, wavelength_log: np.ndarray
    ):
        self.sample_rate = sample_rate

        # Get indices of peaks in the trigger signal.
        self.peaks, _ = find_peaks(trigger_data, height=3, distance=15)

        # Make relative to the first point.
        mod_peaks = self.peaks - self.peaks[0]
        mod_time = mod_peaks / self.sample_rate
        fit = np.polyfit(mod_time, wavelength_log, 2)

        # Create function mapping time to wavelength.
        self.mapping = np.poly1d(fit)

    def process_data(self, raw_data: np.ndarray) -> AnalysisResult:
        """
        Converts raw data to wavelength by interpolating against wavelength logs.

        Parameters
        ----------
        raw_data : ndarray
            The raw data to convert.

        Returns
        -------
        channel_data : dict
            A dictionary of processed data. Has the keys "wavelengths", "data",
            "wavelength_hash", and "data_hash".
        """
        data = raw_data[self.peaks[0] : self.peaks[-1]]

        # Time relative to the first collected data point.
        device_time = np.arange(len(data)) / self.sample_rate

        # Get wavelengths at given times.
        wls = self.mapping(device_time)

        return AnalysisResult(wls, data)


lambda_start = 1500
lambda_stop = 1600
duration = 15
trigger_step = 0.01
power_dBm = 0.0

sample_rate = 50e3
duration = 15
buffer = 4  # Additional time around duration to prevent timeout.
trigger_channel = 1
trigger_level = 1
active_channels = [1, 2, 3, 4]  # Channels to activate and use.


print("getting nameserver")
ns = locate_ns("camacholab.ee.byu.edu")
laser = Proxy(ns.lookup("westview.scarletwitch"))
print("connecting to laser")
laser.autoconnect()

# laser.on()
laser.power_dBm(power_dBm)
laser.open_shutter()
laser.sweep_set_mode(continuous=True, twoway=True, trigger=False, const_freq_step=False)
laser.trigger_enable_output()
triggerMode = laser.trigger_set_mode("Step")
triggerStep = laser.trigger_step(trigger_step)
print("laser configured")

scope = RTO()
scope.connect(address="10.32.112.162", timeout=30e3)
print("scope connected")

channel_setting = {
    # Additional settings to pass to each channel if used.
    1: {"range": 10, "position": -4},
    2: {"range": 5, "position": -4},
    3: {"range": 5, "position": -4},
    4: {"range": 5, "position": -4},
}

acquire_time = duration + buffer
numSamples = int((acquire_time) * sample_rate)

print(f"Connected: {scope.query('*IDN?')}")
scope.acquisition_settings(sample_rate, acquire_time)
for channel in active_channels:
    channelMode = "Trigger" if (channel == trigger_channel) else "Data"
    print("Adding Channel {} - {}".format(channel, channelMode))
    try:
        scope.set_channel(channel, **channel_setting[channel])
    except:
        pass  # hotfix for weird timeout error
# Add trigger.
scope.edge_trigger(trigger_channel, trigger_level)

scope.write("CHAN2:DIGF:STAT ON")
scope.write("CHAN3:DIGF:STAT ON")
scope.write("CHAN4:DIGF:STAT ON")
scope.write("CHAN2:DIGF:CUT 100E+3")
scope.write("CHAN4:DIGF:CUT 100E+3")

print("Starting Acquisition")
scope.acquire(timeout=duration * 3)

print("Sweeping Laser")
laser.sweep_wavelength(lambda_start, lambda_stop, duration)

print("Waiting for acquisition to complete.")
scope.wait_for_device()

# Acquire Data
rawData = [None]  # Ugly hack to make the numbers line up nicely.
rawData[1:] = [scope.get_data(channel) for channel in active_channels]
wavelengthLog = laser.wavelength_logging()
wavelengthLogSize = laser.wavelength_logging_number()


analysis = WavelengthAnalyzer(
    sample_rate=sample_rate,
    wavelength_log=wavelengthLog,
    trigger_data=rawData[trigger_channel],
)


data = [None]  # Really ugly hack to make index numbers line up.
data[1:] = [
    # List comprehension to put all the datasets in this one array.
    analysis.process_data(rawData[channel])
    for channel in active_channels
]

folderPath = "."
for i in range(3):
    np.savez(
        Path(folderPath, f"Channel{i+2}.npz"),
        wavelength=np.array(data[i + 2]["wavelengths"]),
        power=np.array(data[i + 2]["data"]),
    )
