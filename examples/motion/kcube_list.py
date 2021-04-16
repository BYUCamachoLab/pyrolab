import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import *
from thorlabs_kinesis import kcube_dcservo as kc

print(kc.TLI_BuildDeviceList())
print(kc.TLI_GetDeviceListSize())
num = kc.SAFEARRAY()
kc.TLI_GetDeviceList(byref(num))
print(num.cDims)
print(num.fFeatures)
print(num.cbElements)
print(num.cLocks)
print(num.pvData)

num = kc.DeviceList()
length = c_ulong(250)
kc.TLI_GetDeviceListExt(byref(num),length)
print(num.list.decode("utf-8"))
ser_list = str(num.list.decode("utf-8"))

while(ser_list.find(',') != -1):
    ser_no = int(ser_list[0:ser_list.find(',')])
    print(ser_no)

    info = kc.TLI_DeviceInfo()
    hard = kc.TLI_HardwareInformation()
    kc.TLI_GetDeviceInfo(c_char_p(bytes(str(ser_no), "utf-8")),byref(info))
    kc.CC_GetHardwareInfoBlock(c_char_p(bytes(str(ser_no), "utf-8")),byref(hard))
    print(info.typeID)
    print(info.description)
    print(info.PID)
    print(info.motorType)
    print(info.maxChannels)
    print(hard.modelNumber)
    print(hard.serialNumber)

    ser_list = ser_list[ser_list.find(',')+1:]
    
