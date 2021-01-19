# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PRM1Z8
------

Submodule containing drivers for the ThorLabs PRM1Z8 rotational stage.

Contributors
 * Benjamin Arnesen (https://github.com/BenA8)  
 * Christian Carver (https://github.com/cjcarver)
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101, HomingMixin

class PRM1Z8(Motion, KDC101, HomingMixin):
    """
    A PRM1Z8 precision motorized rotation stage controlled by a KCube DC Servo 
    motor.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    """
    def __init__(self, serialno, polling=200):
        super().__init__(serialno, polling)
        self._max_pos=

    def _position_to_du(self, pos: float) -> int:
        """
        Map a position value to the range 0 to SHORT_MAX (which is the range of 
        positions for serial communication).

        Parameters
        ----------
        pos : float
            The position to map in microns.

        Returns
        -------
        pos_du : int
            The position as a percentage of max travel for the given channel
            (device units), range 0 to 32767, equivalent to 0 to 100%.
        """
        POSITION_MAX = self.max_pos
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

    