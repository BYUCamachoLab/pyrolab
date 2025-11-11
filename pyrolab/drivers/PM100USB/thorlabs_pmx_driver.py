# thorlabs_pmx_driver.py
from pyrolab.drivers import Instrument
from pyrolab.api import expose
import socket, json
import subprocess, sys
TLPM_DEFAULT_CHANNEL = 1

class TLPMXError(Exception):
    pass


class ThorlabsPMX(Instrument):
    """
    Proxy-side driver that forwards method calls to the 32-bit helper process
    running TLPMX_32.dll.  Communication is JSON over TCP.
    """

    def __init__(self, host="127.0.0.1", port=6010):
        super().__init__()
        self.host = host
        self.port = port
        self.resource_name = None
        self.connected = False
        
        python32 = r"C:\Users\mw742\AppData\Local\Programs\Python\Python313-32\python.exe"
        script = r"C:\Users\mw742\lab_project\32-bit-helper.py"
        try:
            result = subprocess.check_output(
                'netstat -ano | findstr :6010', shell=True, text=True
            )
            for line in result.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[-1].isdigit() and parts[-1] != "0":
                    pid = parts[-1]
                    subprocess.run(
                        f"taskkill /F /PID {pid}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
        except subprocess.CalledProcessError:
            pass  # no process on port 6010

        subprocess.Popen(
            [python32, script],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        subprocess.Popen([python32, script])
                


    
    def _rpc(self, method, **kwargs):
        payload = json.dumps({"method": method, "params": kwargs}).encode()
        with socket.create_connection((self.host, self.port), timeout=5) as s:
            s.sendall(payload)
            data = json.loads(s.recv(8192))
        if "error" in data:
            raise TLPMXError(data["error"])
        return data.get("result")

    
    @staticmethod
    @expose
    def detect_devices():
        """Ask the helper process for all connected resources."""
        # no need for staticmethod in proxy—forward explicitly if desired
        with socket.create_connection(("127.0.0.1", 6010), timeout=5) as s:
            s.sendall(json.dumps({"method": "detect_devices"}).encode())
            data = json.loads(s.recv(4096))
        if "error" in data:
            raise TLPMXError(data["error"])
        return data["result"]
    
    @expose
    def connect(self, resource=None, id_query=True, do_reset=True):
        result = self._rpc("connect", resource=resource, id_query=id_query, do_reset=do_reset)
        print("gothere")
        self.resource_name = resource
        self.connected = bool(result)
        return self.connected

    @expose
    def autoconnect(self):
        return super().autoconnect()

    @expose
    def set_wavelength_nm(self, wl, channel=TLPM_DEFAULT_CHANNEL):
        self._rpc("set_wavelength_nm", wl=wl, channel=channel)

    @expose
    def set_auto_range(self, on=True, channel=TLPM_DEFAULT_CHANNEL):
        self._rpc("set_auto_range", on=on, channel=channel)

    @expose
    def set_power_unit_watt(self, watt=True, channel=TLPM_DEFAULT_CHANNEL):
        self._rpc("set_power_unit_watt", watt=watt, channel=channel)

    @expose
    def zero(self, channel=TLPM_DEFAULT_CHANNEL):
        self._rpc("zero", channel=channel)

    @expose
    def read_power_w(self, channel=TLPM_DEFAULT_CHANNEL):
        return self._rpc("read_power_w", channel=channel)

    @expose
    def get_wavelength_nm(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """This function returns the user's wavelength in nm. Args: attribute (0=set,1=min,2=max), channel. Returns nm."""
        return self._rpc("get_wavelength_nm", attribute=attribute, channel=channel)

    @expose
    def get_power_autorange(self, channel=TLPM_DEFAULT_CHANNEL):
        """Returns the power auto range mode. Return values: 0=off, 1=on."""
        return self._rpc("get_power_autorange", channel=channel)

    @expose
    def set_power_range_w(self, max_w, channel=TLPM_DEFAULT_CHANNEL):
        """Sets the sensor's power range in watt. Args: max_w, channel."""
        return self._rpc("set_power_range_w", max_w=max_w, channel=channel)

    @expose
    def get_power_range_w(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Returns the power range value in watt. Args: attribute (0=set,1=min,2=max), channel."""
        return self._rpc("get_power_range_w", attribute=attribute, channel=channel)

    @expose
    def set_power_ref(self, val, channel=TLPM_DEFAULT_CHANNEL):
        """Sets the power reference value. Unit per Set Power Unit."""
        return self._rpc("set_power_ref", val=val, channel=channel)

    @expose
    def get_power_ref(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Returns the power reference value. Args: attribute (0=set,1=min,2=max,3=default)."""
        return self._rpc("get_power_ref", attribute=attribute, channel=channel)

    @expose
    def set_power_ref_state(self, on=True, channel=TLPM_DEFAULT_CHANNEL):
        """Sets the power reference state. 0=absolute, 1=relative."""
        return self._rpc("set_power_ref_state", on=on, channel=channel)

    @expose
    def get_power_ref_state(self, channel=TLPM_DEFAULT_CHANNEL):
        """Returns the power reference state. 0=absolute, 1=relative."""
        return self._rpc("get_power_ref_state", channel=channel)

    @expose
    def meas_energy_j(self, channel=TLPM_DEFAULT_CHANNEL):
        """Obtain energy reading in joule [J]."""
        return self._rpc("meas_energy_j", channel=channel)

    @expose
    def meas_voltage_v(self, channel=TLPM_DEFAULT_CHANNEL):
        """Obtain voltage reading in volts [V]."""
        return self._rpc("meas_voltage_v", channel=channel)

    @expose
    def meas_current_a(self, channel=TLPM_DEFAULT_CHANNEL):
        """Obtain current reading in amperes [A]."""
        return self._rpc("meas_current_a", channel=channel)

    @expose
    def meas_frequency_hz(self, channel=TLPM_DEFAULT_CHANNEL):
        """Obtain frequency reading in hertz [Hz]."""
        return self._rpc("meas_frequency_hz", channel=channel)

    @expose
    def meas_power_density_w_per_cm2(self, channel=TLPM_DEFAULT_CHANNEL):
        """Obtain power density reading in W/cm^2."""
        return self._rpc("meas_power_density_w_per_cm2", channel=channel)

    @expose
    def set_beam_diameter_mm(self, mm, channel=TLPM_DEFAULT_CHANNEL):
        """Set beam diameter in millimeter [mm]. Used for power/energy density."""
        return self._rpc("set_beam_diameter_mm", mm=mm, channel=channel)

    @expose
    def get_beam_diameter_mm(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return beam diameter in millimeter [mm]. Args: attribute (0=set,1=min,2=max)."""
        return self._rpc("get_beam_diameter_mm", attribute=attribute, channel=channel)

    @expose
    def set_photodiode_responsivity_aw(self, resp, channel=TLPM_DEFAULT_CHANNEL):
        """Set photodiode responsivity in A/W."""
        return self._rpc("set_photodiode_responsivity_aw", resp=resp, channel=channel)

    @expose
    def get_photodiode_responsivity_aw(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return photodiode responsivity in A/W. Args: attribute (0=set,1=min,2=max,3=default)."""
        return self._rpc("get_photodiode_responsivity_aw", attribute=attribute, channel=channel)

    @expose
    def set_avg_time_s(self, tau_s, channel=TLPM_DEFAULT_CHANNEL):
        """Set averaging time constant in seconds [s]."""
        return self._rpc("set_avg_time_s", tau_s=tau_s, channel=channel)

    @expose
    def get_avg_time_s(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return averaging time constant in seconds [s]."""
        return self._rpc("get_avg_time_s", attribute=attribute, channel=channel)

    @expose
    def set_avg_count(self, n, channel=TLPM_DEFAULT_CHANNEL):
        """Set averaging count (number of samples)."""
        return self._rpc("set_avg_count", n=n, channel=channel)

    @expose
    def get_avg_count(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return averaging count. Args: attribute (0=set,1=min,2=max,3=default)."""
        return self._rpc("get_avg_count", attribute=attribute, channel=channel)

    @expose
    def set_line_frequency_hz(self, hz):
        """Select line frequency. Accepted values: 50 or 60 Hz."""
        return self._rpc("set_line_frequency_hz", hz=hz)

    @expose
    def get_line_frequency_hz(self):
        """Return selected line frequency in Hz."""
        return self._rpc("get_line_frequency_hz")

    @expose
    def set_attenuation_db(self, db, channel=TLPM_DEFAULT_CHANNEL):
        """Set attenuation in dB."""
        return self._rpc("set_attenuation_db", db=db, channel=channel)

    @expose
    def get_attenuation_db(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return attenuation in dB. Args: attribute (0=set,1=min,2=max)."""
        return self._rpc("get_attenuation_db", attribute=attribute, channel=channel)

    @expose
    def get_input_filter_state(self, channel=TLPM_DEFAULT_CHANNEL):
        """Return photodiode input filter state. 0=off, 1=on."""
        return self._rpc("get_input_filter_state", channel=channel)

    @expose
    def set_accel_state(self, on=True, channel=TLPM_DEFAULT_CHANNEL):
        """Set thermopile acceleration state. 0=off, 1=on."""
        return self._rpc("set_accel_state", on=on, channel=channel)

    @expose
    def get_accel_state(self, channel=TLPM_DEFAULT_CHANNEL):
        """Return thermopile acceleration state. 0=off, 1=on."""
        return self._rpc("get_accel_state", channel=channel)

    @expose
    def set_accel_mode_auto(self, auto=True, channel=TLPM_DEFAULT_CHANNEL):
        """Set thermopile acceleration auto mode. 0=manual, 1=auto."""
        return self._rpc("set_accel_mode_auto", auto=auto, channel=channel)

    @expose
    def get_accel_mode(self, channel=TLPM_DEFAULT_CHANNEL):
        """Return thermopile acceleration mode. 0=manual, 1=auto."""
        return self._rpc("get_accel_mode", channel=channel)

    @expose
    def set_accel_tau_s(self, tau_s, channel=TLPM_DEFAULT_CHANNEL):
        """Set thermopile acceleration tau in seconds [s]."""
        return self._rpc("set_accel_tau_s", tau_s=tau_s, channel=channel)

    @expose
    def get_accel_tau_s(self, attribute=0, channel=TLPM_DEFAULT_CHANNEL):
        """Return thermopile acceleration tau in seconds [s]."""
        return self._rpc("get_accel_tau_s", attribute=attribute, channel=channel)

    @expose
    def close(self):
        if self.connected:
            try:
                self._rpc("close")
            finally:
                self.connected = False


