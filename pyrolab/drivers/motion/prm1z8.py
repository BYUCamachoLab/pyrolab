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
from numpy import interp

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101, HomingMixin
from pyrolab.api import expose

@expose
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
    def __init__(self, serialno: str, polling=200, home=False):
        super().__init__(serialno, polling, home)

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
            The position as a percentage of max travel (device units), range 0 to
            32767, equivalent to 0 to 100%.
        """
        pos_du = self._max_pos
        #pos_du = round(interp(pos, [0, POSITION_MAX], [0, SHORT_MAX]))
        return pos_du

    def _du_to_position(self, pos: int) -> float:
        """
        Map a position (device units in the range -SHORT_MAX to SHORT_MAX) to 
        the real unit range -max_pos to max_pos.

        Parameters
        ----------
        pos : int
            The position as a percentage of max travel, range -32767 to 32767 
            equivalent to -100% to 100%.

        Returns
        -------
        pos : int
            The absolute position in degrees.
        """
        pos = self._max_pos
        #pos = interp(int(pos), [-SHORT_MAX, SHORT_MAX], [-POSITION_MAX, POSITION_MAX])
        return pos

    def move(self, position: float) -> None:
        """
        Set the postion of to the given position (radians). 
        
        If the requested position is not in the allowed range, it is set it to 
        minimum or maximum value accordingly.

        Parameters
        ----------
        position : float
            The position to move to in degree.
        """
        
        percent = self._position_to_du(position)
        self.position(percent)

    def jog(self, step: float) -> None:
        """
        Jog the position by some step value in degrees.

        Parameters
        ----------
        step : float
            The amount to jog the stage by (in degrees).
        """
        pos = self.get_position()
        self.move(pos + step)

    def get_position(self) -> float:
        """
        Gets the current position, as measured by the device. 

        Returns
        -------
        position : float
            The current position in degrees.
        """
        # Get the voltage position and map it to an integer position (returns in degree)
        pos_du = self.position()
        return self._du_to_position(pos_du)

    