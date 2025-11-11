# tlpmx_json_server.py  (32-bit Python)
import socket, json, traceback
from ctypes import c_uint32, c_int, c_int16, c_double, c_bool, byref, create_string_buffer
from TLPMX import TLPMX, TLPM_DEFAULT_CHANNEL

tlpm = TLPMX()
current_resource = None

def detect_devices():
    n = c_uint32()
    tlpm.findRsrc(byref(n))
    names = []
    buf = create_string_buffer(1024)
    for i in range(n.value):
        tlpm.getRsrcName(c_int(i), buf)
        names.append(buf.value.decode())
    return names

def connect(resource=None, id_query=True, do_reset=True):
    global current_resource
    if resource is None:
        devs = detect_devices()
        if not devs:
            raise RuntimeError("No devices found")
        resource = devs[0]
    current_resource = resource
    tlpm.open(create_string_buffer(resource.encode()), c_bool(bool(id_query)), c_bool(bool(do_reset)))
    return True

def get_calibration_msg(channel=TLPM_DEFAULT_CHANNEL):
    buf = create_string_buffer(1024)
    tlpm.getCalibrationMsg(buf, c_int16(channel))
    return buf.value.decode(errors="ignore")

def set_wavelength_nm(wl, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setWavelength(c_double(float(wl)), c_int16(int(channel)))
    return True

def set_auto_range(on=True, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPowerAutoRange(c_int16(1 if on else 0), c_int16(int(channel)))
    return True

def set_power_unit_watt(watt=True, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPowerUnit(c_int16(0 if watt else 1), c_int16(int(channel)))
    return True

def read_power_w(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measPower(byref(v), c_int16(int(channel)))
    return float(v.value)

def zero(channel=TLPM_DEFAULT_CHANNEL):
    tlpm.zero(c_int16(int(channel)))
    return True
# ---- PM100USB-compatible helpers ----

def get_wavelength_nm(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getWavelength(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def get_power_autorange(channel=TLPM_DEFAULT_CHANNEL):
    mode = c_int16()
    tlpm.getPowerAutorange(byref(mode), c_int16(int(channel)))
    return int(mode.value)

def set_power_range_w(max_w, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPowerRange(c_double(float(max_w)), c_int16(int(channel)))
    return True

def get_power_range_w(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getPowerRange(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def set_power_ref(val, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPowerRef(c_double(float(val)), c_int16(int(channel)))
    return True

def get_power_ref(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getPowerRef(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def set_power_ref_state(on=True, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPowerRefState(c_int16(1 if on else 0), c_int16(int(channel)))
    return True

def get_power_ref_state(channel=TLPM_DEFAULT_CHANNEL):
    state = c_int16()
    tlpm.getPowerRefState(byref(state), c_int16(int(channel)))
    return int(state.value)

def meas_energy_j(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measEnergy(byref(v), c_int16(int(channel)))
    return float(v.value)

def meas_voltage_v(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measVoltage(byref(v), c_int16(int(channel)))
    return float(v.value)

def meas_current_a(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measCurrent(byref(v), c_int16(int(channel)))
    return float(v.value)

def meas_frequency_hz(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measFreq(byref(v), c_int16(int(channel)))
    return float(v.value)

def meas_power_density_w_per_cm2(channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.measPowerDens(byref(v), c_int16(int(channel)))
    return float(v.value)

def set_beam_diameter_mm(mm, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setBeamDia(c_double(float(mm)), c_int16(int(channel)))
    return True

def get_beam_diameter_mm(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getBeamDia(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def set_photodiode_responsivity_aw(resp, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setPhotodiodeResponsivity(c_double(float(resp)), c_int16(int(channel)))
    return True

def get_photodiode_responsivity_aw(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getPhotodiodeResponsivity(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def set_avg_time_s(tau_s, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAvgTime(c_double(float(tau_s)), c_int16(int(channel)))
    return True

def get_avg_time_s(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getAvgTime(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def set_avg_count(n, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAvgCnt(c_uint32(int(n)), c_int16(int(channel)))
    return True

def get_avg_count(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_uint32()
    tlpm.getAvgCnt(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return int(v.value)

def set_line_frequency_hz(hz, channel=TLPM_DEFAULT_CHANNEL):
    # API expects 50 or 60 as code values
    tlpm.setLineFrequency(c_int16(int(hz)))
    return True

def get_line_frequency_hz():
    v = c_int16()
    tlpm.getLineFrequency(byref(v))
    return int(v.value)

def set_attenuation_db(db, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAttenuation(c_double(float(db)), c_int16(int(channel)))
    return True

def get_attenuation_db(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getAttenuation(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)

def get_input_filter_state(channel=TLPM_DEFAULT_CHANNEL):
    v = c_int16()
    tlpm.getInputFilterState(byref(v), c_int16(int(channel)))
    return int(v.value)

def set_accel_state(on=True, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAccelState(c_int16(1 if on else 0), c_int16(int(channel)))
    return True

def get_accel_state(channel=TLPM_DEFAULT_CHANNEL):
    v = c_int16()
    tlpm.getAccelState(byref(v), c_int16(int(channel)))
    return int(v.value)

def set_accel_mode_auto(auto=True, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAccelMode(c_int16(1 if auto else 0), c_int16(int(channel)))
    return True

def get_accel_mode(channel=TLPM_DEFAULT_CHANNEL):
    v = c_int16()
    tlpm.getAccelMode(byref(v), c_int16(int(channel)))
    return int(v.value)

def set_accel_tau_s(tau_s, channel=TLPM_DEFAULT_CHANNEL):
    tlpm.setAccelTau(c_double(float(tau_s)), c_int16(int(channel)))
    return True

def get_accel_tau_s(attribute=0, channel=TLPM_DEFAULT_CHANNEL):
    v = c_double()
    tlpm.getAccelTau(c_int16(int(attribute)), byref(v), c_int16(int(channel)))
    return float(v.value)


def close():
    tlpm.close()
    return True

DISPATCH = {
    "detect_devices": detect_devices,
    "connect": connect,
    "get_calibration_msg": get_calibration_msg,
    "set_wavelength_nm": set_wavelength_nm,
    "set_auto_range": set_auto_range,
    "set_power_unit_watt": set_power_unit_watt,
    "read_power_w": read_power_w,
    "get_wavelength_nm": get_wavelength_nm,
    "get_power_autorange": get_power_autorange,
    "set_power_range_w": set_power_range_w,
    "get_power_range_w": get_power_range_w,
    "set_power_ref": set_power_ref,
    "get_power_ref": get_power_ref,
    "set_power_ref_state": set_power_ref_state,
    "get_power_ref_state": get_power_ref_state,
    "meas_energy_j": meas_energy_j,
    "meas_voltage_v": meas_voltage_v,
    "meas_current_a": meas_current_a,
    "meas_frequency_hz": meas_frequency_hz,
    "meas_power_density_w_per_cm2": meas_power_density_w_per_cm2,
    "set_beam_diameter_mm": set_beam_diameter_mm,
    "get_beam_diameter_mm": get_beam_diameter_mm,
    "set_photodiode_responsivity_aw": set_photodiode_responsivity_aw,
    "get_photodiode_responsivity_aw": get_photodiode_responsivity_aw,
    "set_avg_time_s": set_avg_time_s,
    "get_avg_time_s": get_avg_time_s,
    "set_avg_count": set_avg_count,
    "get_avg_count": get_avg_count,
    "set_line_frequency_hz": set_line_frequency_hz,
    "get_line_frequency_hz": get_line_frequency_hz,
    "set_attenuation_db": set_attenuation_db,
    "get_attenuation_db": get_attenuation_db,
    "get_input_filter_state": get_input_filter_state,
    "set_accel_state": set_accel_state,
    "get_accel_state": get_accel_state,
    "set_accel_mode_auto": set_accel_mode_auto,
    "get_accel_mode": get_accel_mode,
    "set_accel_tau_s": set_accel_tau_s,
    "get_accel_tau_s": get_accel_tau_s,

    "zero": zero,
    "close": close,
}

def handle(req):
    fn = DISPATCH[req["method"]]
    kwargs = req.get("params", {})
    return fn(**kwargs)

s = socket.socket()
s.bind(("127.0.0.1", 6010))
s.listen(1)
print("Listening at 127.0.0.1")
while True:
    conn, _ = s.accept()
    try:
        req = json.loads(conn.recv(65536))
        res = {"result": handle(req)}
    except Exception:
        res = {"error": traceback.format_exc()}
    conn.send(json.dumps(res).encode())
    conn.close()
