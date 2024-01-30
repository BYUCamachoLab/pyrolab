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
        
    def scope_open(self, sampling_frequency: float = 20e6, buffer_size: int = 0, 
                   offset: float = 0, amplitude_range: float = 5):
        """
        Initialize the oscilloscope.

        parameters
        ----------
        sampling_frequency : float, default: 20e6 
            Sampling frequency of the oscilloscope in Hz.
        buffer_size : int, default: 0
            Buffer size of the oscilloscope in data points, a value of 0 means maximum buffer size.
        offset : int, default: 0
            Offset voltage of the oscilloscope in Volts.
        amplitude_range : int, default: 5
            Amplitude range of the oscilloscope in Volts.
        """
        scope.open(self._device_data, sampling_frequency, buffer_size, offset, amplitude_range)
    
    def scope_close(self):
        """
        close (reset) the oscilloscope.
        """
        scope.close(self._device_data)

    def scope_measure(self, channel: int = 1):
        """
        Measure the voltage on a channel.

        Parameters
        ----------
        channel : int {1, 2}
            The selected oscilloscope channel
        
        Returns
        -------
        data : float
            The measured voltage in Volts
        """
        data = scope.measure(self._device_data, channel)
        return data
    
    def scope_trigger(self, enable: bool, source: str = "none", channel: int = 1, 
                      timeout: float = 0, edge_rising: bool = True, level: float = 0):
        """
        Set up the triggering for the scope.

        Parameters
        ----------
        enable : bool
            Enable or disable triggering.
        source : str, default: "none"
            Trigger source, possible: "none", "analog", "digital", "external_[1-4]" (ie: "external_1")
        channel : int, default: 1
            Trigger channel, possible options: 1-4 for analog, or 0-15 for digital
        timeout : int, default: 0
            Auto trigger timeout in seconds, default is 0
        edge_rising : bool, default: True
            Trigger edge rising - True means rising, False means falling, default is rising
        level : int, default: 0
            Trigger level in Volts, default is 0V
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
        
    def scope_record(self, channel: int = 1):
        """
        Record an analog signal over a period of time determined by the scope buffer and sample rate.

        Parameters
        ----------
        channel : int, default: 1
            The selected oscilloscope channel
        
        Returns
        -------
        data : list[float]
            A list with the recorded voltages
        """

        data = scope.record(self._device_data, channel)
        return data
    
    def get_scope_settings(self):
        """
        Get the scope's sample rate, buffer size, and max buffer size.

        Returns
        -------
        info : dict
            A dictionary with the scope info: sample_rate, buffer_size, max_buffer_size
        """
        info = {"sample_rate" : scope.data.sampling_frequency,
                "buffer_size" : scope.data.buffer_size,
                "max_buffer_size" : scope.data.max_buffer_size}
        return info
    
    def get_scope_sample_rate(self):
        """
        Get the scope sample rate.

        Returns
        -------
        sample_rate : float
            The scope sample rate in Hz
        """
        sample_rate = scope.data.sampling_frequency
        return sample_rate
    
    def wavegen_generate(self, channel: int = 1, function: str = "sine", 
                         offset: float = 0, frequency: float = 1e03, amplitude: float = 1, 
                         symmetry: float = 50, wait: float = 0, run_time: float = 0, 
                         repeat: int = 0, data: list[float] = []):
        """
            Generate a waveform on a wavegen channel.

            Parameters
            ----------
            channel : int, default: 1
                The selected wavegen channel
            function : str, default: "sine"
                The function (shape) of the generated waveform, possible: 
                "custom", "sine", "square", "triangle", "noise", "ds", "pulse", 
                "trapezium", "sine_power", "ramp_up", "ramp_down"
            offset : float, default: 0
                Offset voltage in Volts
            frequency : float, default: 1e03
                Frequency in Hz
            amplitude : float, default: 1
                Amplitude in Volts
            symmetry : float, default: 50
                Signal symmetry in percentage
            wait : float, default: 0
                Wait time in seconds
            run_time : float, default: 0
                Run time in seconds, default is infinite (0)
            repeat : int, default: 0
                Repeat count, default is infinite (0)
            data : list[float], default: []
                List of voltages, used only if function=custom
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
        
    def wavegen_close(self, channel: int = 0):
        """
        Reset a wavegen channel, or all channels (channel=0).
        
        Parameters
        ----------
        channel : int, default: 0
            The selected wavegen channel
        """
        wavegen.close(self._device_data, channel)

    def wavegen_enable(self, channel: int = 1):
        """
        Enable a wavegen channel, starting the waveform generation.
        
        Parameters
        ----------
        channel : int, default: 1
            The selected wavegen channel
        """

        wavegen.enable(self._device_data, channel)
        
    def wavegen_disable(self, channel: int = 1):
        """
        Disable a wavegen channel, stopping the waveform generation.
        
        Parameters
        ----------
        channel : int, default: 1
            The selected wavegen channel
        """
        wavegen.disable(self._device_data, channel)