# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
AnalogDiscovery
=======



Driver for the Digilent Analog Discovery 3.

.. attention::

   Requires the waveform SDK from Digilent

   .. _github.com: https://github.com/Digilent/WaveForms-SDK-Getting-Started-PY#egg=WF_SDK

   which can be installed with "pip install git+https://github.com/Digilent/WaveForms-SDK-Getting-Started-PY#egg=WF_SDK"

.. admonition:: Dependencies
   :class: note

   WF_SDK (`repository <https://github.com/Digilent/WaveForms-SDK-Getting-Started-PY#egg=WF_SDK>`_)
"""


from WF_SDK import device, scope, wavegen, tools, error 

from pyrolab.drivers.FPGAs import FPGA
from pyrolab.api import expose, behavior

@behavior(instance_mode="single")
@expose
class AnalogDiscovery(FPGA):
    """
    A Digilent Analog Discovery 3.
    
    The board has 2 analog inputs, 2 analog outputs, 16 digital inputs, and 16 digital outputs.
    At the moment, only the analog inputs and outputs are implemented, and only the scope and wavegen
    functionalities are implemented.
    
    Attributes
    ----------
    _device_data : device
        The device data object from the WaveForms SDK. Stores information about the device.
    
    """    
    def autoconnect(self):
        """
        Connect to the board.
        
        """
        self._device_data = device.open()
        if self._device_data.name == "Digital Discovery":
            device.close(self._device_data)
            raise Exception("This is a Digital Discovery, not an Analog Discovery.")
    
    def close(self):
        """
        Disconnect from the board.
        
        """
        device.close(self._device_data)
        
    def scope_open(self, sampling_frequency=20e06, buffer_size=0, offset=0, amplitude_range=5):
        """
        initialize the oscilloscope

        parameters:- sampling frequency in Hz, default is 20MHz
                    - buffer size, default is 0 (maximum)
                    - offset voltage in Volts, default is 0V
                    - amplitude range in Volts, default is ±5V
        """
        scope.open(self._device_data, sampling_frequency, buffer_size, offset, amplitude_range)
    
    def scope_close(self):
        """
        close (reset) the oscilloscope
        """
        scope.close(self._device_data)

    def scope_measure(self, channel):
        """
        measure the voltage on a channel

        parameters:- channel, 1 or 2
        
        returns:    - the measured voltage in Volts
        """
        return scope.measure(self._device_data, channel)
    
    def scope_trigger(self, enable, source="none", channel=1, timeout=0, edge_rising=True, level=0):
        """
            set up triggering

            parameters: - device data
                        - enable / disable triggering with True/False
                        - trigger source - possible: "none", "analog", "digital", "external_[1-4]" (ie: "external_1")
                        - trigger channel - possible options: 1-4 for analog, or 0-15 for digital
                        - auto trigger timeout in seconds, default is 0
                        - trigger edge rising - True means rising, False means falling, default is rising
                        - trigger level in Volts, default is 0V
        """
        
        if source == "none":
            source = scope.trigger_source.none
        elif source == "analog":
            source = scope.trigger_source.analog
        elif source == "digital":
            source = scope.trigger_source.digital
        elif source.startswith("external_"):
            channel = int(source.split("_")[1])
            source = scope.trigger_source.external[channel]
            
        scope.trigger(self._device_data, enable, source, channel, timeout, edge_rising, level)
        
    def scope_record(self, channel=1):
        """
        record an analog signal

        parameters: - device data
                    - the selected oscilloscope channel (1-2, or 1-4)

        returns:    - a list with the recorded voltages
        """
        return scope.record(self._device_data, channel)
    
    def get_scope_info(self):
        """
        get the scope info

        returns:    - a dictionary with the scope info
        """
        info = {"sample_rate" : scope.data.sampling_frequency,
                "buffer_size" : scope.data.buffer_size,
                "max_buffer_size" : scope.data.max_buffer_size}
        return info
    
    def get_scope_sample_rate(self):
        """
        get the scope sample rate

        returns:    - the scope sample rate in Hz
        """
        return scope.data.sampling_frequency
    
    def wavegen_generate(self, channel=1, function="sine", offset=0, frequency=1e03, amplitude=1, symmetry=50, wait=0, run_time=0, repeat=0, data=[]):
        """
            generate an analog signal

            parameters: - device data
                        - the selected wavegen channel (1-2)
                        - function - possible: "custom", "sine", "square", "triangle", "noise", "ds", "pulse", "trapezium", "sine_power", "ramp_up", "ramp_down" (from wavegen.function)
                        - offset voltage in Volts
                        - frequency in Hz, default is 1KHz
                        - amplitude in Volts, default is 1V
                        - signal symmetry in percentage, default is 50%
                        - wait time in seconds, default is 0s
                        - run time in seconds, default is infinite (0)
                        - repeat count, default is infinite (0)
                        - data - list of voltages, used only if function=custom, default is empty
        """
        if function == "custom":
            function = wavegen.function.custom
        elif function == "sine":
            function = wavegen.function.sine
        elif function == "square":
            function = wavegen.function.square
        elif function == "triangle":
            function = wavegen.function.triangle
        elif function == "noise":
            function = wavegen.function.noise
        elif function == "ds":
            function = wavegen.function.ds
        elif function == "pulse":
            function = wavegen.function.pulse
        elif function == "trapezium":
            function = wavegen.function.trapezium
        elif function == "sine_power":
            function = wavegen.function.sine_power
        elif function == "ramp_up":
            function = wavegen.function.ramp_up
        elif function == "ramp_down":
            function = wavegen.function.ramp_down
            
        wavegen.generate(self._device_data, channel, function, offset, frequency, amplitude, symmetry, wait, run_time, repeat, data)
        
    def wavegen_close(self, channel=0):
        """
        reset a wavegen channel, or all channels (channel=0)
        """
        wavegen.close(self._device_data, channel)

    def wavegen_enable(self, channel=1):
        """
        enable a wavegen channel

        parameters: - the selected wavegen channel (1-2)
        """
        wavegen.enable(self._device_data, channel)
        
    def wavegen_disable(self, channel=1):
        """
        disable a wavegen channel
        
        parameters: - the selected wavegen channel (1-2)
        """
        wavegen.disable(self._device_data, channel)