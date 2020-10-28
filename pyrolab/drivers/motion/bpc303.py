

import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Kinesis" + ";" + os.environ['PATH']
#print(os.environ['PATH']) 
from threading import Thread
import thorlabs_kinesis as tk
import time
import keyboard
from ctypes import (
    c_short,
    c_char_p,
    c_void_p,
    byref,
    c_int,
    create_string_buffer,
)
from ctypes.wintypes import (
    DWORD,
    WORD,
)

from thorlabs_kinesis import benchtop_piezo as bp

serialno = c_char_p(bytes("","utf-8"))
xHome = c_short(16383)
yHome = c_short(16383)
zHome = c_short(16383)

xCurr = 0
yCurr = 0
zCurr = 0

def map_point(pos):
    vol = round(pos*32767/20000)
    print(vol)
    if(vol > 32767):
        vol = 32767
    if(vol < 0):
        vol = 0
    print(c_short(vol))
    return c_short(vol)

def map_vol(vol):
    point = round(vol*20000/32767)
    return point


def get_serial():
    global serialno
    serialList = c_char_p(bytes("","utf-8"))
    bp.TLI_GetDeviceListByTypeExt(serialList, 250, 71)  # get list of serial numbers of benchtop-piezo devices connected
    serialno = c_char_p(serialList.value[ : -1]) # assume there is only one device connected - the 8 digit serial number retrieved

def open_serial():
    global serialno
    bp.PBC_Open(serialno)       # open the device for communication
    bp.PBC_StartPolling(serialno,bp.Channel1,c_int(200))    # start polling each channel every 200 ms
    bp.PBC_StartPolling(serialno,bp.Channel2,c_int(200))
    bp.PBC_StartPolling(serialno,bp.Channel3,c_int(200))


def home():
    global serialno
    global xHome
    global yHome
    global zHome
    global xCurr
    global yCurr
    global zCurr
    bp.PBC_SetPosition(serialno,bp.Channel1,xHome)    # set the position
    bp.PBC_SetPosition(serialno,bp.Channel2,yHome)
    bp.PBC_SetPosition(serialno,bp.Channel3,zHome)
    xCurr = map_vol(xHome.value)
    yCurr = map_vol(yHome.value)
    zCurr = map_vol(zHome.value)
    time.sleep(3)

def set_home(x,y,z):
    global xHome
    global yHome
    global zHome
    xHome =  map_point(x)
    yHome =  map_point(y)
    zHome =  map_point(z)

def enable_channels():
    global serialno
    bp.PBC_EnableChannel(serialno, bp.Channel1)
    bp.PBC_EnableChannel(serialno, bp.Channel2)
    bp.PBC_EnableChannel(serialno, bp.Channel3)

def zero(channel):
    global serialno
    bp.PBC_SetZero(serialno, channel)
    time.sleep(30)

def zero_X():
    global serialno
    global xCurr
    bp.PBC_SetZero(serialno, bp.Channel1)
    xCurr = 0

def zero_Y():
    global serialno
    global yCurr
    bp.PBC_SetZero(serialno, bp.Channel2)
    yCurr = 0

def zero_Z():
    global serialno
    global zCurr
    bp.PBC_SetZero(serialno, bp.Channel3)
    zCurr = 0

def zero_all():
    zero_X()
    zero_Y()
    zero_Z()
    time.sleep(30)

def start_polling():
    global serialno
    bp.PBC_StartPolling(serialno,bp.Channel1,c_int(200))    # start polling each channel every 200 ms
    bp.PBC_StartPolling(serialno,bp.Channel2,c_int(200))
    bp.PBC_StartPolling(serialno,bp.Channel3,c_int(200))
    bp.PBC_ClearMessageQueue(serialno)  # clear prior messages
    time.sleep(1)   # pause 1 sec
    bp.PBC_SetPositionControlMode(serialno,bp.Channel1,c_int(2))
    bp.PBC_SetPositionControlMode(serialno,bp.Channel2,c_int(2))
    bp.PBC_SetPositionControlMode(serialno,bp.Channel3,c_int(2))
    time.sleep(0.5)

def stop_polling():
    global serialno
    bp.PBC_StopPolling(serialno,bp.Channel1)
    bp.PBC_StopPolling(serialno,bp.Channel2)
    bp.PBC_StopPolling(serialno,bp.Channel3)

def disconnect():
    global serialno
    done = 0
    for i in range(10):
        if bp.PBC_Disconnect(serialno) == 0:
            done = 1
            break
        else:
            time.sleep(1)
    return done

def set_pos(channel,pos):
    global serialno
    bp.PBC_SetPosition(serialno,channel,map_point(pos))
    time.sleep(1)

def set_X(pos):
    global serialno
    global xCurr
    bp.PBC_SetPosition(serialno,bp.Channel1,map_point(pos))
    xCurr = pos
    time.sleep(1)

def set_Y(pos):
    global serialno
    global yCurr
    bp.PBC_SetPosition(serialno,bp.Channel2,map_point(pos))
    yCurr = pos
    time.sleep(1)

def set_Z(pos):
    global serialno
    global zCurr
    bp.PBC_SetPosition(serialno,bp.Channel3,map_point(pos))
    zCurr = pos
    time.sleep(1)

def move_to(xPos,yPos,zPos):
    set_X(xPos)
    set_Y(yPos)
    set_Z(zPos)

def jog(step,channel):
    set_pos(get_pos(channel) + step,channel)

def jog_X(step):
    global xCurr
    print(xCurr)
    #set_X(get_X() + step)
    set_X(xCurr + step)

def jog_Y(step):
    global yCurr
    #set_Y(get_Y() + step)
    set_Y(yCurr + step)

def jog_Z(step):
    global zCurr
    #set_Z(get_Z() + step)
    set_Z(zCurr + step)

def jog_all(xStep,yStep,zStep):
    jog_X(xStep)
    jog_Y(yStep)
    jog_Z(zStep)

def get_pos(channel):
    global serialno
    pos = int(bp.PBC_GetPosition(serialno,channel))
    return map_vol(pos)

def get_X():
    global serialno
    pos = int(bp.PBC_GetPosition(serialno,bp.Channel1))
    return map_vol(pos)

def get_Y():
    global serialno
    pos = int(bp.PBC_GetPosition(serialno,bp.Channel2))
    return map_vol(pos)

def get_Z():
    global serialno
    pos = int(bp.PBC_GetPosition(serialno,bp.Channel3))
    return map_vol(pos)

def get_all():
    global serialno
    xPos = get_X()
    yPos = get_Y()
    zPos = get_Z()
    return xPos,yPos,zPos

def start():
    if bp.TLI_BuildDeviceList() != 0:
        return 0
    if bp.TLI_GetDeviceListSize() == 0:
        return 0
    get_serial()
    open_serial()
    enable_channels()
    start_polling()
    return 1

def end():
    global serialno
    stop_polling()
    dis = disconnect()
    bp.PBC_Close(serialno)
    return dis