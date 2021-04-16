import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import c_int, c_double, c_short, byref, pointer
from thorlabs_kinesis import kcube_dcservo as kc

num = c_short(0)
kc.TLI_GetDeviceListSize(byref(num))
print(num)