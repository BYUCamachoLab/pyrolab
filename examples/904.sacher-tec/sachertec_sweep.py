import os
import time
import math
import keyboard

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

def flush_input():
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        import sys, termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def keyDebounce():
    time.sleep(0.2) # sleep 200 ms 

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

print("what is the low wavelength (nm)?")
wl_low = float(input())

print("what is the high wavelength (nm)?")
wl_high = float(input())

print("what velocity would you like it to move at (nm/s)?")
vel = vel_to_du(float(input()))

acc = acc_to_du(1.0)

keyhandle = epm.VCS_OpenDevice(name,protocol,interface,port,byref(pErrorCode))

ret=epm.VCS_SetState(keyhandle, NodeID, ST_ENABLED, byref(pErrorCode))

ret=epm.VCS_SetPositionProfile(keyhandle, NodeID, c_dword(vel), c_dword(acc), c_dword(acc), byref(pErrorCode))

ret=epm.VCS_MoveToPosition(keyhandle, NodeID, wl_to_du(wl_low), 1, 0, byref(pErrorCode))

print("Sweeping")
print("Press 'q' to quit")

comp = False
while(comp == False):
    ret=epm.VCS_GetMovementState(keyhandle, NodeID, byref(pTargetReached), byref(pErrorCode))
    comp = pTargetReached.value
    if keyboard.is_pressed('q'):
        keyDebounce() # key 'debouncer'
        flush_input()
        comp = True
        epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
        print(f"Position: {du_to_wl(pPositionIs.value)}")

sweep_done = False
init_time = time.time()
while(sweep_done == False):
    ret=epm.VCS_MoveToPosition(keyhandle, NodeID, wl_to_du(wl_high), 1, 0, byref(pErrorCode))
    comp = False
    while(comp == False):
        ret=epm.VCS_GetMovementState(keyhandle, NodeID, byref(pTargetReached), byref(pErrorCode))
        comp = pTargetReached.value
        if keyboard.is_pressed('q'):
            keyDebounce() # key 'debouncer'
            flush_input()
            comp = True
            sweep_done = True
        if(time.time() - init_time > 1):
            init_time = time.time()
            epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
            print(f"Position: {du_to_wl(pPositionIs.value)}")

    if(sweep_done):
        continue

    ret=epm.VCS_MoveToPosition(keyhandle, NodeID, wl_to_du(wl_low), 1, 0, byref(pErrorCode))
    comp = False
    while(comp == False):
        ret=epm.VCS_GetMovementState(keyhandle, NodeID, byref(pTargetReached), byref(pErrorCode))
        comp = pTargetReached.value
        if keyboard.is_pressed('q'):
            keyDebounce() # key 'debouncer'
            flush_input()
            comp = True
            sweep_done = True
        if(time.time() - init_time > 1):
            init_time = time.time()
            epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
            print(f"Position: {du_to_wl(pPositionIs.value)}")
    
epm.VCS_GetPositionIs(keyhandle, NodeID, byref(pPositionIs), byref(pErrorCode))
print(f"Position: {du_to_wl(pPositionIs.value)}")

ret=epm.VCS_SetState(keyhandle, NodeID, ST_DISABLED, byref(pErrorCode))
ret=epm.VCS_CloseAllDevices(byref(pErrorCode))
print("laser closed")