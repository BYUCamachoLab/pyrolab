import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import *
from thorlabs_kinesis import kcube_dcservo as kc
import time

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
    print(kc.TLI_GetDeviceInfo(c_char_p(bytes(str(ser_no), "utf-8")),byref(info)))
      
    modelNo = c_char()  
    mn_size = c_ulong(8)  
    type_1 = c_ushort(0)  
    numChannels = c_ushort(0)
    notes = c_char()
    sizeOfNotes = c_ulong(48)
    firmwareVersion = c_ulong(0)
    hardwareVersion = c_ushort(0)
    modificationState = c_ushort(0)

    print(kc.CC_GetHardwareInfo(c_char_p(bytes(str(ser_no), "utf-8")),byref(modelNo),
        mn_size,
        byref(type_1),
        byref(numChannels),
        byref(notes),
        sizeOfNotes,
        byref(firmwareVersion),
        byref(hardwareVersion),
        byref(modificationState)))
    print(ser_no)

    kc.CC_Open(c_char_p(bytes(str(ser_no), "utf-8")))
    kc.CC_LoadSettings(c_char_p(bytes(str(ser_no), "utf-8")))
    kc.CC_StartPolling(c_char_p(bytes(str(ser_no), "utf-8")), c_int(200))

    print("travel mode:")
    print(kc.CC_GetMotorTravelMode(c_char_p(bytes(str(ser_no), "utf-8"))))

    print(kc.CC_GetStageAxisMaxPos(c_char_p(bytes(str(ser_no), "utf-8"))))

    min_pos = c_double()
    max_pos = c_double()
    print(kc.CC_GetMotorTravelMode(c_char_p(bytes(str(ser_no), "utf-8")),byref(min_pos),byref(max_pos)))
    print("range:")
    print(min_pos)
    print(max_pos)

    print(info.typeID)
    print(info.description)
    print(info.PID)
    print(info.motorType)
    print(info.maxChannels)
    print(modelNo)
    print(notes)

    kc.CC_Close(c_char_p(bytes(str(ser_no), "utf-8")))

    ser_list = ser_list[ser_list.find(',')+1:]
    
