"""
Only works with 64-bit Python TLPMX.py is under Thorlabs github and is under the MIT license 
"""

from pyrolab.drivers import Instrument
from pyrolab.api import expose
from ctypes import *
from TLPMX import TLPMX, TLPM_DEFAULT_CHANNEL


class TLPMXError(Exception):
    pass


def safe_call(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            try:
                msg = repr(e)
                print(f"[ThorlabsPMX.safe_call] {func.__name__} failed with: {msg}")
            except Exception:
                pass

            try:
                if getattr(self, "connected", False):
                    self.close()
            finally:
                raise
    return wrapper



# Explicitly unsupported calls for PM100USB (based on TLPMX documentation)
INCOMPATIBLE_PM100USB_METHODS = {
    "confBurstArrayMeasCurrentChannel",
    "confBurstArrayMeasPowerChannel",
    "confBurstArrayMeasVoltageChannel",
    "confBurstArrayMeasTrigger",
    "confCurrentMeasurementSequence",
    "confPowerMeasurementSequence",
    "confVoltageMeasurementSequence",
    "confEnergyMeasurementSequence",
    "startBurstArrayMeasurement",
    "startMeasurementSequence",
    "zeroDevice",    # Not present for PM100USB
}


# Methods with pointer / “use with byref” outputs that we want to make safe
# for remote use. These are handled by explicit wrappers below.
POINTER_WRAPPER_MAP = {
    # Basic measurements
    "measPower": "_wrap_measPower",
    "measCurrent": "_wrap_measCurrent",
    "measVoltage": "_wrap_measVoltage",
    "measPowerDens": "_wrap_measPowerDens",
    "measEnergyDens": "_wrap_measEnergyDens",
    "measDualChannelSimultaneous": "_wrap_measDualChannelSimultaneous",

    # Device/system info
    "getBatteryVoltage": "_wrap_getBatteryVoltage",
    "getDispBrightness": "_wrap_getDispBrightness",
    "getDispContrast": "_wrap_getDispContrast",
    "getInputFilterState": "_wrap_getInputFilterState",
    "getLineFrequency": "_wrap_getLineFrequency",
    "getSummertime": "_wrap_getSummertime",
    "getTime": "_wrap_getTime",
    "readRegister": "_wrap_readRegister",

    # Streaming / state
    "getFetchState": "_wrap_getFetchState",
    "getNextFastArrayMeasurement": "_wrap_getNextFastArrayMeasurement",
    "getNextFastArrayMeasurementRelativeTime": "_wrap_getNextFastArrayMeasurementRelativeTime",
}

METHOD_DESCRIPTIONS = {
    # Basic configuration
    "setWavelength": "Set the sensor wavelength (nm) for calibration.",
    "setPowerUnit": "Set the unit for power measurements (0 = W).",
    "setPowerAutoRange": "Enable/disable autoranging for power.",
    "setCurrentAutoRange": "Enable/disable autoranging for current.",
    "setVoltageAutoRange": "Enable/disable autoranging for voltage.",

    # Scalar measurements
    "measPower": "Measure average optical power on the given channel (W).",
    "measCurrent": "Measure input current on the given channel (A).",
    "measVoltage": "Measure input voltage on the given channel (V).",
    "measPowerDens": "Measure power density on the given channel.",
    "measEnergyDens": "Measure energy density on the given channel.",
    "measDualChannelSimultaneous": "Measure two channels simultaneously (returns tuple).",

    # Info / status
    "getBatteryVoltage": "Read battery voltage of the device.",
    "getDispBrightness": "Get display brightness setting.",
    "getDispContrast": "Get display contrast setting.",
    "getInputFilterState": "Get digital filter state for the given channel.",
    "getLineFrequency": "Get mains line frequency detected by the device.",
    "getSummertime": "Get daylight saving time (summertime) mode.",
    "getTime": "Get current date/time from the device.",
    "readRegister": "Read a register from the device firmware.",
    "getFetchState": "Get measurement fetch state (not supported on PM100USB).",

    # Fast array (not actually supported for PM100USB; here just for completeness)
    "getNextFastArrayMeasurement": "Retrieve next block of fast array samples (timestamps + values).",
    "getNextFastArrayMeasurementRelativeTime": "Fast array samples with relative timestamps.",
}

class ThorlabsPMX(Instrument):
    """
    Unified driver for Thorlabs PM100USB using TLPMX.

    - All TLPMX methods are still available dynamically.
      Anything not listed in POINTER_WRAPPER_MAP is forwarded
      directly by call().
    - Methods in POINTER_WRAPPER_MAP allocate ctypes objects on
      the server and return plain Python values.
    """

    def __init__(self, resource=None):
        super().__init__()
        self.resource_name = resource
        self.dev = None
        self.connected = False

    def _check_supported(self, name: str):
        if name in INCOMPATIBLE_PM100USB_METHODS:
            raise TLPMXError(f"Method '{name}' is not supported on PM100USB.")

    # ------------------------------------------------------------------
    # Discovery / connection
    # ------------------------------------------------------------------

    @staticmethod
    @expose
    def detect_devices():
        tlpm = TLPMX()
        n = c_int32()
        tlpm.findRsrc(byref(n))

        devices = []
        buf = create_string_buffer(256)

        for i in range(n.value):
            tlpm.getRsrcName(c_int(i), buf)
            devices.append(buf.value.decode())

        return devices

    @expose
    @safe_call
    def connect(self, resource=None, id_query=True, do_reset=True):
        if resource is None:
            resource = self.resource_name

        if resource is None:
            raise TLPMXError("No VISA resource provided.")

        self.resource_name = resource
        self.dev = TLPMX()
        self.dev.open(resource.encode(), id_query, do_reset)
        self.connected = True
        return True

    @expose
    @safe_call
    def autoconnect(self):
        devs = ThorlabsPMX.detect_devices()
        if not devs:
            raise TLPMXError("No TLPMX compatible devices found.")
        return self.connect(devs[0])

    @expose
    def close(self):
        if self.connected and self.dev:
            self.dev.close()
            self.connected = False

    @expose
    def list_available_methods(self):
        methods = []
        for name in dir(self.dev):
            if name.startswith("_"):
                continue
            if callable(getattr(self.dev, name)):
                if name not in INCOMPATIBLE_PM100USB_METHODS:
                    methods.append(name)
        return sorted(methods)

    # ------------------------------------------------------------------
    # Pointer-output wrappers (server side only)
    # ------------------------------------------------------------------

    # Scalar measurement wrappers

    def _wrap_measPower(self, channel: int = TLPM_DEFAULT_CHANNEL) -> float:
        power = c_double()
        self.dev.measPower(byref(power), c_uint16(channel))
        return float(power.value)

    def _wrap_measCurrent(self, channel: int = TLPM_DEFAULT_CHANNEL) -> float:
        current = c_double()
        self.dev.measCurrent(byref(current), c_uint16(channel))
        return float(current.value)

    def _wrap_measVoltage(self, channel: int = TLPM_DEFAULT_CHANNEL) -> float:
        voltage = c_double()
        self.dev.measVoltage(byref(voltage), c_uint16(channel))
        return float(voltage.value)

    def _wrap_measPowerDens(self, channel: int = TLPM_DEFAULT_CHANNEL) -> float:
        power_dens = c_double()
        self.dev.measPowerDens(byref(power_dens), c_uint16(channel))
        return float(power_dens.value)

    def _wrap_measEnergyDens(self, channel: int = TLPM_DEFAULT_CHANNEL) -> float:
        energy_dens = c_double()
        self.dev.measEnergyDens(byref(energy_dens), c_uint16(channel))
        return float(energy_dens.value)

    def _wrap_measDualChannelSimultaneous(self, measurement: int) -> tuple:
        ch1 = c_double()
        ch2 = c_double()
        self.dev.measDualChannelSimultaneous(
            c_uint16(measurement),
            byref(ch1),
            byref(ch2),
        )
        return float(ch1.value), float(ch2.value)

    # Device/system info

    def _wrap_getBatteryVoltage(self) -> float:
        voltage = c_double()
        self.dev.getBatteryVoltage(byref(voltage))
        return float(voltage.value)

    def _wrap_getDispBrightness(self) -> float:
        val = c_double()
        self.dev.getDispBrightness(byref(val))
        return float(val.value)

    def _wrap_getDispContrast(self) -> float:
        val = c_double()
        self.dev.getDispContrast(byref(val))
        return float(val.value)

    def _wrap_getInputFilterState(self, channel: int = TLPM_DEFAULT_CHANNEL) -> int:
        state = c_int16()
        self.dev.getInputFilterState(byref(state), c_uint16(channel))
        return int(state.value)

    def _wrap_getLineFrequency(self) -> int:
        line_freq = c_int16()
        self.dev.getLineFrequency(byref(line_freq))
        return int(line_freq.value)

    def _wrap_getSummertime(self) -> int:
        mode = c_int16()
        self.dev.getSummertime(byref(mode))
        return int(mode.value)

    def _wrap_getTime(self) -> dict:
        year = c_int16()
        month = c_int16()
        day = c_int16()
        hour = c_int16()
        minute = c_int16()
        second = c_int16()
        self.dev.getTime(
            byref(year),
            byref(month),
            byref(day),
            byref(hour),
            byref(minute),
            byref(second),
        )
        return {
            "year": int(year.value),
            "month": int(month.value),
            "day": int(day.value),
            "hour": int(hour.value),
            "minute": int(minute.value),
            "second": int(second.value),
        }

    def _wrap_readRegister(self, reg: int) -> int:
        value = c_int16()
        self.dev.readRegister(c_int16(reg), byref(value))
        return int(value.value)

    # Streaming / state

    def _wrap_getFetchState(self, channel: int = TLPM_DEFAULT_CHANNEL) -> int:
        state = c_int16()
        self.dev.getFetchState(byref(state), c_uint16(channel))
        return int(state.value)

    def _wrap_getNextFastArrayMeasurement(
        self,
        max_count: int,
        channel: int = TLPM_DEFAULT_CHANNEL,
    ) -> dict:
        """
        Wrapper around TLPMX.getNextFastArrayMeasurement.

        Args:
            max_count: maximum number of samples to retrieve (<= 200).
            channel: sensor channel.

        Returns:
            dict with keys:
                'count' (int),
                'timestamps' (list[int]),
                'values' (list[float])
        """
        max_count = int(max_count)
        if max_count <= 0:
            return {"count": 0, "timestamps": [], "values": []}

        count = c_uint32(max_count)
        timestamps_array = (c_uint32 * max_count)()
        values_array = (c_float * max_count)()

        self.dev.getNextFastArrayMeasurement(
            byref(count),
            timestamps_array,
            values_array,
            c_uint16(channel),
        )

        n = int(count.value)
        n = min(max(n, 0), max_count)

        timestamps = [int(timestamps_array[i]) for i in range(n)]
        values = [float(values_array[i]) for i in range(n)]

        return {"count": n, "timestamps": timestamps, "values": values}

    def _wrap_getNextFastArrayMeasurementRelativeTime(
        self,
        max_count: int,
        channel: int = TLPM_DEFAULT_CHANNEL,
    ) -> dict:
        """
        Wrapper around TLPMX.getNextFastArrayMeasurementRelativeTime.

        Same signature and return type as _wrap_getNextFastArrayMeasurement,
        but timestamps are already converted to relative time.
        """
        max_count = int(max_count)
        if max_count <= 0:
            return {"count": 0, "timestamps": [], "values": []}

        count = c_uint32(max_count)
        timestamps_array = (c_uint32 * max_count)()
        values_array = (c_float * max_count)()

        self.dev.getNextFastArrayMeasurementRelativeTime(
            byref(count),
            timestamps_array,
            values_array,
            c_uint16(channel),
        )

        n = int(count.value)
        n = min(max(n, 0), max_count)

        timestamps = [int(timestamps_array[i]) for i in range(n)]
        values = [float(values_array[i]) for i in range(n)]

        return {"count": n, "timestamps": timestamps, "values": values}

    # ------------------------------------------------------------------
    # Generic dynamic call
    # ------------------------------------------------------------------

    @expose
    @safe_call
    def call(self, tlp_method, *args):
        """
        Forward any method call to TLPMX dynamically.

        Example:
            pm.call("setWavelength", 1550.0, 1)

        For methods listed in POINTER_WRAPPER_MAP, this method
        allocates ctypes objects on the server and returns plain
        Python values, so the client never sees pointers.
        """
        if not self.connected:
            raise RuntimeError("Device not connected")

        self._check_supported(tlp_method)

        if tlp_method in POINTER_WRAPPER_MAP:
            wrapper_name = POINTER_WRAPPER_MAP[tlp_method]
            wrapper = getattr(self, wrapper_name)
            return wrapper(*args)

        fn = getattr(self.dev, tlp_method)

        c_args = []
        for a in args:
            if isinstance(a, float):
                c_args.append(c_double(a))
            elif isinstance(a, int):
                c_args.append(c_int16(a))
            elif isinstance(a, str):
                c_args.append(a.encode())
            else:
                c_args.append(a)

        return fn(*c_args)

    @expose
    def method_catalog(self, max_desc_len=80, core_only=False):
        if self.dev is None:
            return ""

        lines = []
        for name in dir(self.dev):
            if name.startswith("_"):
                continue
            obj = getattr(self.dev, name)
            if not callable(obj):
                continue
            if name in INCOMPATIBLE_PM100USB_METHODS:
                continue

            if core_only:
                if not (
                    name.startswith("meas")
                    or name.startswith("setPower")
                    or name.startswith("setCurrent")
                    or name.startswith("setVoltage")
                    or name == "setWavelength"
                ):
                    continue

            desc = METHOD_DESCRIPTIONS.get(name, "")
            if not desc:
                doc = getattr(obj, "__doc__", None)
                if doc:
                    desc = doc.strip().splitlines()[0]
            desc = desc or ""

            if max_desc_len is not None and max_desc_len > 3 and len(desc) > max_desc_len:
                desc = desc[: max_desc_len - 3] + "..."

            name_col = name.ljust(30)
            lines.append(f"{name_col} {desc}")

        lines.sort()
        return "\n".join(lines)


