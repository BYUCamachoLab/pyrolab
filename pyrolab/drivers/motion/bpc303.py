# equipment: Thorlabs Benchtop Piezo BCP303 (3 channel piezo controller)
#            Code designed specifically for ThorLabs NanoMax 300 Stage (3 Channel) connection to BCP303,
#            but can be used with other modules.

#            call open() to open serial comunication with any BCP303 connected
#            make sure to call end() after done using the benchtop piezo

# October 30, 2020
# David Hill
# email: hillda3141@gmail.com

import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Kinesis" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs
import time
from thorlabs_kinesis import benchtop_piezo as bp

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

serialno = c_char_p(bytes("","utf-8"))  #serial number of the BPC303

xMax = 20000    #values for each axis maximum
yMax = 20000
zMax = 20000

xHome = c_short(16383)      #home values
yHome = c_short(16383)
zHome = c_short(16383)

xCurr = 0   #the value of each axis is stored in the program rather than retrieving it every time, this helps with moving precision
yCurr = 0
zCurr = 0

def map_point(pos,channel):     #map a position value to 0-32767 which is the range of positions for serial communication
    vol = 0
    global xMax
    global yMax
    global zMax
    if channel - bp.Channel1:
        vol = round(pos*32767/xMax) #if dealing with the x axis, map using xMax
    if channel - bp.Channel2:
        vol = round(pos*32767/yMax) #if dealing with the y axis, map using yMax
    if channel - bp.Channel2:
        vol = round(pos*32767/zMax) #if dealing with the z axis, map using zMax
    #print(vol)
    if(vol > 32767):    #if the value is out of range, set to either max or min value
        vol = 32767
    if(vol < 0):
        vol = 0
    #print(c_short(vol))
    return c_short(vol)

def map_vol(loc,channel):   #map a serial-recieved value or voltage to 0-maxValue range of a given channel
    point = 0
    global xMax
    global yMax
    global zMax
    vol = int(loc)
    if channel - bp.Channel1:
        point = round(vol*xMax/32767)   #depending on the channel, map the voltage to the position
    if channel - bp.Channel2:
        point = round(vol*yMax/32767)
    if channel - bp.Channel2:
        point = round(vol*zMax/32767)
    return point


def get_serial():   #retrieves the serial number of the connected device
    global serialno
    serialList = c_char_p(bytes("","utf-8"))
    bp.TLI_GetDeviceListByTypeExt(serialList, 250, 71)  # get list of serial numbers of benchtop-piezo devices connected
    serialno = c_char_p(serialList.value[ : -1]) # assume there is only one device connected - the 8 digit serial number retrieved

def open_serial():  #opens serial communication and starts polling from the benchtop piezo
    global serialno
    bp.PBC_Open(serialno)       # open the device for communication
    start_polling()


def home():     #homes all three axis
    global serialno
    global xHome
    global yHome
    global zHome
    global xCurr
    global yCurr
    global zCurr
    bp.PBC_SetPosition(serialno,bp.Channel1,xHome)    # set the position to the stored home values
    bp.PBC_SetPosition(serialno,bp.Channel2,yHome)
    bp.PBC_SetPosition(serialno,bp.Channel3,zHome)
    xCurr = map_vol(xHome,bp.Channel1)    # set the current position by maping the home values to position
    yCurr = map_vol(yHome,bp.Channel2)
    zCurr = map_vol(zHome,bp.Channel3)
    time.sleep(3)   #give it time to settle

def set_home(x,y,z):    #set a new home position for the axises
    global xHome
    global yHome
    global zHome
    xHome =  map_point(x,bp.Channel1)   # set the new home values by maping the position to voltage
    yHome =  map_point(y,bp.Channel2)
    zHome =  map_point(z,bp.Channel3)

def enable_channels():  #enables all three channels for communication
    global serialno
    bp.PBC_EnableChannel(serialno, bp.Channel1)
    bp.PBC_EnableChannel(serialno, bp.Channel2)
    bp.PBC_EnableChannel(serialno, bp.Channel3)

def max_travel():   #retirieves the max amount of movement for each axis
    global serialno
    global xMax
    global yMax
    global zMax
    x = int(bp.PBC_GetMaxTravel(serialno,bp.Channel1))*100      #ask for the max travel of each axis
    if x > 0:       #if it returns zero, this function is not supported by the module and we use the default max value (20000)
        xMax = x
    y = int(bp.PBC_GetMaxTravel(serialno,bp.Channel2))*100
    if y > 0:
        yMax = y
    z = int(bp.PBC_GetMaxTravel(serialno,bp.Channel3))*100
    if z > 0:
        zMax = z
    #print(xMax,yMax,zMax)
    return xMax,yMax,zMax

def zero(channel):      #will zero the given channel
    global serialno
    bp.PBC_SetZero(serialno, channel)   #zero it and give it time (20-30 sec)
    time.sleep(30)

def zero_X():       #will zero the first channel (x)
    global serialno
    global xCurr
    bp.PBC_SetZero(serialno, bp.Channel1)   #zero it, but it does NOT pause
    xCurr = 0                               #should mainly be called from zero_all() function and not directly

def zero_Y():       #will zero the second channel (y)
    global serialno
    global yCurr
    bp.PBC_SetZero(serialno, bp.Channel2)   #zero it, but it does NOT pause
    yCurr = 0                               #should mainly be called from zero_all() function and not directly

def zero_Z():       #will zero the third channel (z)
    global serialno
    global zCurr
    bp.PBC_SetZero(serialno, bp.Channel3)   #zero it, but it does NOT pause
    zCurr = 0                               #should mainly be called from zero_all() function and not directly

def zero_all():     #zeros all three axises
    zero_X()
    zero_Y()
    zero_Z()
    time.sleep(30)  #pause to give it time

def start_polling():    #function starts polling data from device
    global serialno
    bp.PBC_StartPolling(serialno,bp.Channel1,c_int(200))    # start polling each channel every 200 ms
    bp.PBC_StartPolling(serialno,bp.Channel2,c_int(200))
    bp.PBC_StartPolling(serialno,bp.Channel3,c_int(200))
    bp.PBC_ClearMessageQueue(serialno)  # clear prior messages
    time.sleep(1)   # pause 1 sec
    bp.PBC_SetPositionControlMode(serialno,bp.Channel1,c_int(2))    #set the mode to closed operation
    bp.PBC_SetPositionControlMode(serialno,bp.Channel2,c_int(2))
    bp.PBC_SetPositionControlMode(serialno,bp.Channel3,c_int(2))
    time.sleep(0.5)

def stop_polling(): #stop polling data from device
    global serialno
    bp.PBC_StopPolling(serialno,bp.Channel1)
    bp.PBC_StopPolling(serialno,bp.Channel2)
    bp.PBC_StopPolling(serialno,bp.Channel3)

def disconnect():   #disconnect from the device
    global serialno
    done = 0
    for i in range(10):     #try up to 10 times to disconnect (it doesn't go through every so often)
        if bp.PBC_Disconnect(serialno) == 0:
            done = 1    #if we successfully disconnect, return 1
            break
        else:
            time.sleep(1)
    return done     #this will be 0 if we failed to disconnect

def set_pos(pos,channel):   #set the postion of a certain axis to the given position (nm), if not in the allowed range, set it to min or max value
    global serialno
    bp.PBC_SetPosition(serialno,channel,map_point(pos,channel)) #map the point to voltage and set the position
    if channel == bp.Channel1:
        xCurr = map_vol(map_point(pos,channel))
    if channel == bp.Channel2:
        yCurr = map_vol(map_point(pos,channel))
    if channel == bp.Channel3:
        yCurr = map_vol(map_point(pos,channel))
    time.sleep(1)

def set_X(pos):     #set the position of the x axis to the inputed position (nm), if not in the allowed range, set it to min or max value
    global serialno
    global xCurr
    bp.PBC_SetPosition(serialno,bp.Channel1,map_point(pos,bp.Channel1)) #map the point to voltage set the position
    xCurr = map_vol(map_point(pos,bp.Channel1))
    time.sleep(1)

def set_Y(pos):     #set the position of the y axis to the inputed position (nm), if not in the allowed range, set it to min or max value
    global serialno
    global yCurr
    bp.PBC_SetPosition(serialno,bp.Channel2,map_point(pos,bp.Channel2)) #map the point and set the position
    yCurr = map_vol(map_point(pos,bp.Channel2))
    time.sleep(1)

def set_Z(pos):     #set the poistion of the z axis to the inputed position (nm), if not in the allowed range, set it to min or max value
    global serialno
    global zCurr
    bp.PBC_SetPosition(serialno,bp.Channel3,map_point(pos,bp.Channel3)) #map the point and set the position
    zCurr = map_vol(map_point(pos,bp.Channel3))
    time.sleep(1)

def move_to(xPos,yPos,zPos):    #set all three values (nm)
    set_X(xPos)
    set_Y(yPos)
    set_Z(zPos)

def jog(step,channel):      #set a channel's position to the current position plus the inputed step value (nm)
    set_pos(get_pos(channel) + step,channel)

def jog_X(step):    #set the x axis value to the current position plus the inputed step value (nm)
    global xCurr
    print(xCurr)
    #set_X(get_X() + step)
    set_X(xCurr + step)

def jog_Y(step):    #set the y axis value to the current position plus the inputed step value (nm)
    global yCurr
    #set_Y(get_Y() + step)
    set_Y(yCurr + step)

def jog_Z(step):    #set the z axis value to the current position plus the inputed step value (nm)
    global zCurr
    #set_Z(get_Z() + step)
    set_Z(zCurr + step)

def jog_all(xStep,yStep,zStep):     #jog each axis by the inputed amounts
    jog_X(xStep)
    jog_Y(yStep)
    jog_Z(zStep)

def get_pos(channel):   #returns the current position of the inputed channel
    global serialno
    pos = bp.PBC_GetPosition(serialno,channel)  #get the voltage position and map it to an integer position (returns in nm)
    return map_vol(pos,channel)

def get_X():    #returns the current x position
    global serialno
    pos = bp.PBC_GetPosition(serialno,bp.Channel1)  #get the voltage and map it to an integer position (returns in nm)
    return map_vol(pos,bp.Channel1)

def get_Y():    #returns the current y position
    global serialno
    pos = bp.PBC_GetPosition(serialno,bp.Channel2)  #map voltage to an integer position (nm)
    return map_vol(pos,bp.Channel2)

def get_Z():    #returns the current z position
    global serialno
    pos = bp.PBC_GetPosition(serialno,bp.Channel3)  #map the voltage to an integer position (nm)
    return map_vol(pos,bp.Channel3)

def get_all():  #returns the current positions of each, as measured by the device (nm)
    global serialno
    xPos = get_X()
    yPos = get_Y()
    zPos = get_Z()
    return xPos,yPos,zPos

def start():    #function finds a benchtop piezo and initiates communication
    if bp.TLI_BuildDeviceList() != 0:   #if there are errors building devices
        return 0
    if bp.TLI_GetDeviceListSize() == 0: #if there are no devices
        return 0
    get_serial()    #get the serial number of the BP303
    open_serial()   #open communication
    enable_channels()
    max_travel()
    start_polling() #start polling data
    return 1

def end():  #function closes the communication channel with the BP303
    global serialno
    stop_polling()
    dis = disconnect()  #attempt to disconnect, if unsuccessful return 0
    bp.PBC_Close(serialno)
    return dis