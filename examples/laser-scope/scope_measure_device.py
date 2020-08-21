# ---------------------------------------------------------------------------- #
# Parameters
# ---------------------------------------------------------------------------- #
#Laser Sweep
lambda_start    = 1500
lambda_stop     = 1600
duration        = 15
trigger_step    = 0.01
power_dBm       = 12
#Data Collection
sample_rate     = 10e09
buffer          = 2 #Additional time around duration to prevent timeout.

#Save Data
#The first argument passed will be used as the file name.
filename_prefix = ""
filename_suffix = "data_now"
data_directory  = "measurements/"
append_date     = True #Appends date to the beginning of the directory.
save_raw_data   = True #Save raw data collected from devices.

#Oscilloscope
scope_IP        = "10.32.112.162" #Oscilloscope IP Address
take_screenshot = True
active_channels = [1,2,3,4] #Channels to activate and use.
trigger_channel = 1 #Channel for trigger signal.
trigger_level   = 1 #Voltage threshold for postitive slope edge trigger.
channel_setting = {
    #Additional settings to pass to each channel if used.
    1: {"range": 10, "position": 2}, 
    2: {"range": 5, "position": -4},
    3: {"range": 5, "position": -2},
    4: {"range": 5, "position": 0.5}
}

# ---------------------------------------------------------------------------- #
# Libraries
# ---------------------------------------------------------------------------- #
import os
from pathlib import Path
#import time
import sys
from datetime import datetime

from pyrolab.drivers.lasers.tsl550 import TSL550
from pyrolab.drivers.scopes.rohdeschwarz import RTO

from data_processing import WavelengthAnalyzer, VisualizeData

# ---------------------------------------------------------------------------- #
# Check Input
# ---------------------------------------------------------------------------- #
# Get command line arguments.
args = sys.argv[1:]
filename = filename_prefix + sys.argv[0] + filename_suffix

# Check laser sweep rate
sweep_rate = (lambda_stop - lambda_start) / duration
assert sweep_rate > 1.0 and sweep_rate < 100.0
# Check laser wavelength range
assert lambda_start >= TSL550.MINIMUM_WAVELENGTH and lambda_stop <= TSL550.MAXIMUM_WAVELENGTH

# ---------------------------------------------------------------------------- #
# Initialize Save Directory
# ---------------------------------------------------------------------------- #
today = datetime.now()
datePrefix = "{}_{}_{}_{}_{}_".format(today.year, today.month, today.day, today.hour, today.minute)
prefix = datePrefix if append_date else ""
folderName = prefix + data_directory
folderPath = Path(Path.cwd(), folderName)
print("Saving data to {} in current directory.".format(folderName))
if not os.path.exists(folderPath):
    print("Creating {} directory.".format(folderName))
    os.makedirs(folderPath)

# ---------------------------------------------------------------------------- #
# Initialize Devices
# ---------------------------------------------------------------------------- #
# Initialize Laser
print("Initializing laser.")
try:
    # Remote Computer via PyroLab
    from pyrolab.api import locate_ns, Proxy
    ns = locate_ns(host="camacholab.ee.byu.edu")
    laser = Proxy(ns.lookup("lasers.TSL550"))
except:
    # Local Computer
    laser = TSL550("COM4")

laser.on()
laser.power_dBm(power_dBm)
laser.open_shutter()
laser.sweep_set_mode(continuous=True, twoway=True, trigger=False, const_freq_step=False)
print("Enabling laser's trigger output.")
laser.trigger_enable_output()
triggerMode = laser.trigger_set_mode("Step")
triggerStep = laser.trigger_set_step(trigger_step)
print("Setting trigger to: {} and step to {}".format(triggerMode, triggerStep))

#Get number of samples to record. Add buffer just in case.
acquire_time = duration + buffer
numSamples = int((acquire_time) * sample_rate)
print("Set for {:.2E} Samples @ {:.2E} Sa/s.".format(numSamples, sample_rate))

#Oscilloscope Settings
print("Initializing Oscilloscope")
scope = RTO(scope_IP)
scope.acquisition_settings(sample_rate, acquire_time)
for channel in active_channels:
    channelMode = "Trigger" if (channel == trigger_channel) else "Data"
    print("Adding Channel {} - {}".format(channel, channelMode))
    scope.set_channel(channel, **channel_setting[channel])
#Add trigger.
print("Adding Edge Trigger @ {} Volt(s).".format(trigger_level))
scope.edge_trigger(trigger_channel, trigger_level)

# ---------------------------------------------------------------------------- #
# Collect Data
# ---------------------------------------------------------------------------- #
print('Starting Acquisition')
scope.start_acquisition(timeout = duration*3)

print('Sweeping Laser')
laser.sweep_wavelength(lambda_start, lambda_stop, duration)

print('Waiting for acquisition to complete.')
scope.wait_for_device()

if take_screenshot:
    scope.screenshot(folderName + "screenshot.png")

#Acquire Data
rawData = [None] #Ugly hack to make the numbers line up nicely.
rawData[1:] = [scope.get_data_ascii(channel) for channel in active_channels]
wavelengthLog = laser.wavelength_logging()
wavelengthLogSize = laser.wavelength_logging_number()

#Optional Save Raw Data
if save_raw_data:
    print("Saving raw data.")
    for channel in active_channels:
        with open(folderName + "CHAN{}_Raw.txt".format(channel), "w") as out:
            out.write(str(rawData[channel]))
    with open(folderName + "Wavelength_Log.txt", "w") as out:
        out.write(str(wavelengthLog))

# ---------------------------------------------------------------------------- #
# Process Data
# ---------------------------------------------------------------------------- #
print("Processing Data")
analysis = WavelengthAnalyzer(
    sample_rate = sample_rate,
    wavelength_log = wavelengthLog,
    trigger_data = rawData[trigger_channel]
)

print('=' * 30)
print("Expected number of wavelength points: " + str(int(wavelengthLogSize)))
print("Measured number of wavelength points: " + str(analysis.num_peaks()))
print('=' * 30)

data = [None] #Really ugly hack to make index numbers line up.
data[1:] = [
    #List comprehension to put all the datasets in this one array.
    analysis.process_data(rawData[channel]) for channel in active_channels
]

print("Raw Datasets: {}".format(len(rawData)))
print("Datasets Returned: {}".format((len(data))))

# ---------------------------------------------------------------------------- #
# Generate Visuals & Save Data
# ---------------------------------------------------------------------------- #
for channel in active_channels:
    if (channel != trigger_channel):
        print("Displaying data for channel " + str(channel))
        VisualizeData(folderName + filename, channel, **(data[channel]))
