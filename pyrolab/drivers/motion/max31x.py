# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
ThorLabs 3-Axis NanoMax Flexure Stages
======================================

Submodule containing drivers for the ThorLabs NanoMax 300 piezo controlled
motion stage.

.. attention::

   Windows only.

   Requires ThorLabs Kinesis software. Download it at `thorlabs.com`_.

   .. _thorlabs.com: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=10285

.. admonition:: Dependencies
   :class: note

   thorlabs_kinesis (:ref:`installation instructions <Thorlabs Kinesis Package>`)

.. tip::

   If you are using the remote functionalities of PyroLab, you may see the
   error ``RuntimeError: FT_DeviceNotFound`` when calling functions on objects
   inheriting from KDC101. This sometimes occus when you forget to call
   ``autoconnect()`` before trying to use the device.
"""

import logging

from numpy import interp
from Pyro5.api import behavior, expose

from pyrolab.drivers.motion.kinesis.bpc303 import BPC303


log = logging.getLogger(__name__)


SHORT_MAX = 32767


@behavior(instance_mode="single")
@expose
class MAX31X(BPC303):
    """
    A 3-Axis NanoMax stage controlled by a BPC303 piezo controller.

    Assumes that the following physical mappings of the devices are true:

    .. table::
   
        ==== =======
        Axis Channel
        ==== =======
        x    1
        y    2
        z    3
        ==== =======

    Sets a default home position at the halfway point of the full travel for 
    each channel.
    
    Attributes
    ----------
    X_MAX : int
        Maximum travel for the first channel (nm)
    Y_MAX : int
        Maximum travel for the second channel (nm)
    Z_MAX : int
        Maximum travel for the third channel (nm)

    Notes
    -----
    This class inherits from :py:class:`pyrolab.drivers.motion.kinesis.bpc303.BPC303`. 
    Therefore, all public methods available to that class are available
    here. Note that the functions `position` and `voltage` should not be used,
    but rather `move` from this class.
    """

    def connect(self, serialno: str = "", poll_period: int=200, closed_loop: bool=True, smoothed: bool=False) -> None:
        """
        Connect to the device.

        Parameters
        ----------
        serialno : int
            The serial number of the device to connect to.
        polling : int
            The polling rate in milliseconds.
        closed_loop : bool, optional
            Puts controller in open or closed loop mode. Open loop if False 
            (closed loop allows for positional commands instead of voltage 
            commands), default True.
        smoothed : bool, optional
            Puts controller in smoothed start/stop mode, default False.
        """
        super().connect(serialno=serialno,
                         poll_period=poll_period,
                         closed_loop=closed_loop,
                         smoothed=smoothed)
        # Values for each axis maximum
        self.max_pos = [val / 10 for val in self.max_travel]

    @property
    def X_MAX(self):
        return self.max_pos[0]

    @property
    def Y_MAX(self):
        return self.max_pos[1]

    @property
    def Z_MAX(self):
        return self.max_pos[2]

    def _position_to_du(self, channel: int, pos: float) -> int:
        """
        Map a position value to the range 0 to SHORT_MAX (which is the range of 
        positions for serial communication).

        Parameters
        ----------
        channel : int
            The channel to map (1-n).
        pos : float
            The position to map in microns.

        Returns
        -------
        pos_du : int
            The position as a percentage of max travel for the given channel
            (device units), range 0 to 32767, equivalent to 0 to 100%.
        """
        POSITION_MAX = self.max_pos[channel-1]
        pos_du = round(interp(pos, [0, POSITION_MAX], [0, SHORT_MAX]))
        return pos_du

    def _du_to_position(self, channel: int, pos: int) -> float:
        """
        Map a position (device units in the range -SHORT_MAX to SHORT_MAX) to 
        the real unit range -max_pos to max_pos for a given channel.

        Parameters
        ----------
        channel : int
            The channel to map (1-n).
        pos : int
            The position as a percentage of max travel for the given channel, 
            range -32767 to 32767 equivalent to -100% to 100%.

        Returns
        -------
        pos : int
            The absolute position in microns.
        """
        POSITION_MAX = self.max_pos[channel-1]
        pos = interp(int(pos), [-SHORT_MAX, SHORT_MAX], [-POSITION_MAX, POSITION_MAX])
        return pos

    def move(self, channel: int, position: float) -> None:
        """
        Set the postion of a certain axis to the given position (nm). 
        
        If the requested position is not in the allowed range, it is set it to 
        minimum or maximum value accordingly.

        Parameters
        ----------
        channel : int
            The channel to reposition (1-n).
        position : float
            The position to move to in microns.
        """
        percent = self._position_to_du(channel, position)
        self.position(channel, percent)

    def move_all(self, x: float, y: float, z: float) -> None:
        """
        Move all three channels simultaneously.
        
        Parameters
        ----------
        x : float
            The desired x-position in microns.
        y : float
            The desired y-position in microns.
        z : float
            The desired z-position in microns.
        """
        self.move(1, x)
        self.move(2, y)
        self.move(3, z)

    def jog(self, channel: int, step: float) -> None:
        """
        Jog a channel's position by some step value in micrometers.

        Parameters
        ----------
        channel : int
            The channel to jog.
        step : float
            The amount to jog the channel by (in microns).
        """
        pos = self.get_position(channel)
        self.move(channel, pos + step)

    def get_position(self, channel: int=None) -> float:
        """
        Gets the current position of the requested channel, as measured by the 
        device. Gets all three channels if no channel is specified.

        Parameters
        ----------
        channel : int, optional
            The channel to get the position for. If not specified, gets 
            position of all channels.

        Returns
        -------
        position : float or [float]
            The current position in microns. A single float for a specific
            channel, or an array (length 3) for all channels.
        """
        # Get the voltage position and map it to an integer position (returns in nm)
        if channel is not None:
            pos_du = self.position(channel)
            return self._du_to_position(channel, pos_du)
        else:
            pos = []
            for chan in self.channels:
                pos_du = self.position(chan)
                pos.append(self._du_to_position(chan, pos_du))
            return pos
