from pyrolab.api import locate_ns, Proxy

with locate_ns(host="localhost") as ns:
    uri = ns.lookup("thorlabs_pmx_driver")

print(uri)
with Proxy(uri) as pmx:
    devices = pmx.detect_devices()
    print(devices)
    check = pmx.connect()
    print(check)
    pmx.set_power_unit_watt()
    pmx.set_auto_range()
    pmx.set_wavelength_nm(1555)
    power = pmx.read_power_w()  
    print("Power [W]:", power)
    pmx.close()

# from thorlabs_pmx_driver import ThorlabsPMX
# pmx = ThorlabsPMX()
# devices = pmx.detect_devices()
# print(devices)
# check = pmx.connect()
# print(check)
# pmx.set_power_unit_watt()
# pmx.set_auto_range()
# pmx.set_wavelength_nm(1555)
# power = pmx.read_power_w()
# print("Power [W]:", power)
# pmx.close()
