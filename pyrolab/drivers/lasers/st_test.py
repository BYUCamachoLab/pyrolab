import os
import time
import math

from ctypes import *

from sacher_tec._utils import (
    c_word,
    c_dword,
    bind,
    not_implemented,
)

os.environ['PATH'] = ("C:\\Program Files\\SacherLasertechnik\\MotorMotion 2.1\\data"
+ ";" + os.environ['PATH'])

epos = cdll.LoadLibrary("EposCmd64.dll")

from sacher_tec import epos_motor as epm

ST_DISABLED = c_word(0)
ST_ENABLED = c_word(1)
A_COEF = -3.499E-12
B_COEF = 7.74529E-5
C_COEF = 960.024
WL_MAX = 985.5
WL_MIN = 919.5

def du_to_wl(du):
    wl = A_COEF*(math.pow(du,2)) + B_COEF*du + C_COEF
    if(wl < WL_MIN):
        return WL_MIN
    elif(wl > WL_MAX):
        return WL_MAX
    else:
        return wl

def wl_to_du(wl):
    if(wl < WL_MIN):
        wl = WL_MIN
    elif(wl > WL_MAX):
        wl = WL_MAX
    du = -1*B_COEF/(2*A_COEF) - math.sqrt((wl - C_COEF)/A_COEF + math.pow((B_COEF/(2*A_COEF)),2))
    return round(du)

def vel_to_du(vel):
    if(vel > 30):
        vel = 30
    if(vel < 0.01):
        vel = 0.01
    du = round(vel*380)
    return du

def du_to_vel(du):
    vel = du/3
    if(vel > 30):
        vel = 30
    if(vel < 0.01):
        vel = 0.01
    return vel

def acc_to_du(acc):
    if(acc > 25):
        acc = 25
    if(acc < 0.01):
        acc = 0.01
    du = round(acc*380)
    return du

def du_to_acc(du):
    acc = du/380
    if(acc > 25):
        acc = 25
    if(acc < 0.01):
        acc = 0.01
    return acc

name = create_string_buffer(("EPOS2").encode('utf-8'))
protocol = create_string_buffer(("MAXON SERIAL V2").encode('utf-8'))
interface = create_string_buffer(("USB").encode('utf-8'))
port = create_string_buffer(("USB0").encode('utf-8'))
NodeID = 1
pNbOfBytesRead=c_uint()
pData=c_uint()
pPositionIs=c_long()
pErrorCode=c_int()
pMode=c_byte()
pState=c_word()
pTargetReached=c_bool()
pProfileVelocity=c_dword()
pProfileAcceleration=c_dword()
pProfileDeceleration=c_dword()

print("what wavelength would you like (nm)?")
wl = float(input())

print("what velocity would you like it to move at (nm/s)?")
vel = vel_to_du(float(input()))

print("what acceleration would you like it to move at (nm/s^2)?")
acc = acc_to_du(float(input()))

print("initialize")
keyhandle = epm.VCS_OpenDevice(name,protocol,interface,port,byref(pErrorCode))
print(pErrorCode)
print(keyhandle)

print("get operation mode")
ret=epm.VCS_GetOperationMode(keyhandle, NodeID, byref(pMode), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pMode)

print("get state")
ret=epm.VCS_GetState(keyhandle, NodeID, byref(pState), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pState)

print("set state")
ret=epm.VCS_SetState(keyhandle, NodeID, ST_ENABLED, byref(pErrorCode))
print(pErrorCode)
print(ret)

print("get state")
ret=epm.VCS_GetState(keyhandle, NodeID, byref(pState), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pState)

print("get params")
ret=epm.VCS_GetPositionProfile(keyhandle, NodeID, byref(pProfileVelocity), byref(pProfileAcceleration), byref(pProfileDeceleration),byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pProfileVelocity)
print(pProfileAcceleration)
print(pProfileDeceleration)

print("set params")
ret=epm.VCS_SetPositionProfile(keyhandle, NodeID, c_dword(vel), c_dword(acc), c_dword(acc), byref(pErrorCode))
print(pErrorCode)
print(ret)

print("get params")
ret=epm.VCS_GetPositionProfile(keyhandle, NodeID, byref(pProfileVelocity), byref(pProfileAcceleration), byref(pProfileDeceleration),byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pProfileVelocity)
print(pProfileAcceleration)
print(pProfileDeceleration)

print("get position")
ret = epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(du_to_wl(pPositionIs.value))
init_pos = pPositionIs.value

print("start time:")
init_time = time.time()
print(init_time)

print("set position")
ret=epm.VCS_MoveToPosition(keyhandle, NodeID, wl_to_du(wl), 1, 0, byref(pErrorCode))
print(pErrorCode)
print(ret)

comp = False
while(comp == False):
    # print("check if complete")
    ret=epm.VCS_GetMovementState(keyhandle, NodeID, byref(pTargetReached), byref(pErrorCode))
    # print(pErrorCode)
    # print(ret)
    # print(pTargetReached)
    comp = pTargetReached.value
    epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
    print(du_to_wl(pPositionIs.value))
    time.sleep(0.1)

print("end time:")
end_time = time.time()
print(end_time)

print("difference:")
diff = end_time - init_time
print(diff)

print("get position")
ret=epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(du_to_wl(pPositionIs.value))

end_pos = pPositionIs.value

print("distance traveled:")
dist = abs(end_pos - init_pos)
print(dist)

print("velocity:")
vel = dist/diff
print(vel)

print("set state")
ret=epm.VCS_SetState(keyhandle, NodeID, ST_DISABLED, byref(pErrorCode))
print(pErrorCode)
print(ret)

print("get state")
ret=epm.VCS_GetState(keyhandle, NodeID, byref(pState), byref(pErrorCode))
print(pErrorCode)
print(ret)
print(pState)

print("close device")
ret=epm.VCS_CloseAllDevices(byref(pErrorCode))
print(pErrorCode)
print(ret)