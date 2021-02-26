"""
Author: David Hill
Modified: 2/26/2021
A script that acts as a server to lock and unlock pyrolab devices. The sever is accessed through web sockets, port 8765.
"""

import asyncio
import websockets
import sys
from pyrolab.api import locate_ns, Proxy

def get_names(reference):
    """
    The web socket client will include a 3-character key phrase in order to request an action. The three characters are mapped to
    pyrolab service names in this function.
    """
    name = ""
    if(reference == "TSL"):
        name = "TSL550"
    elif(reference == "PPC"):
        name = "PPCL550"
    elif(reference == "PP2"):
        name = "PPCL551"
    elif(reference == "MIC"):
        name = "UC480"
    elif(reference == "LAM"):
        name = "LAMP"
    elif(reference == "KCU"):
        name = "KCUBES"
    return name

def get_status(name):
    """
    Function returns if the device is locked or not. It will instantiate a Proxy pyrolab object using the given name and will
    request its status.
    """
    try:
        ns = locate_ns(host="camacholab.ee.byu.edu")
        service = Proxy(ns.lookup(name))
        status = service.get_status()
        service._pyroRelease()
        if status == True:
            return 1
        else:
            return 0
    except:
        return -1

def lock(name,user):
    """
    Function instantiates a Proxy pyrolab object with the inputed name and locks it.
    """
    try:
        ns = locate_ns(host="camacholab.ee.byu.edu")
        service = Proxy(ns.lookup(name))
        stat = service.lock(user)
        service._pyroRelease()
        if stat == 1:
            return "LOCKED"
        else:
            return "UNLOCKED"
    except:
        return "UNLOCKED"

def unlock(name,user):
    """
    Function instantiates a Proxy pyrolab object with the inputed name and releases it.
    """
    try:
        ns = locate_ns(host="camacholab.ee.byu.edu")
        service = Proxy(ns.lookup(name))
        stat = service.release(user)
        service._pyroRelease()
        if stat == 1:
            return "UNLOCKED"
        else:
            return "LOCKED"
    except:
        return "LOCKED"

def get_user(name):
    """
    Function instantiates a Proxy pyrolab object with the inputed name and requests the user that is using it.
    If it is not in use it will return a "". However, returning a "" does not mean that is necessarily not in use.
    """
    try:
        ns = locate_ns(host="camacholab.ee.byu.edu")
        service = Proxy(ns.lookup(name))
        user = service.get_user()
        service._pyroRelease()
        return user
    except:
        return ""

def refresh():
    """
    Function checks the status of all pyrolab objects, returning a string of "L"s "U"s and "-" for locked, unlocked, and offline.
    """
    names = ["TSL550","PPCL550","PPCL551","UC480","LAMP","KCUBES"]
    status = []
    users = ""
    for name in names:
        s = get_status(name)
        status.append(s)
        users = users + ":"
        if s == 1:
            users = users + get_user(name)

    msg = ""
    print(status[0])
    if status[0] == 1:
        msg = msg + "L"
    elif status[0] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[1] == 1 and status[2] == 1 and status[3] == 1 and status[4] == 1 and status[5] == 1:
        msg = msg + "L"
    elif status[1] == 0 and status[2] == 0 and status[3] == 0 and status[4] == 0 and status[5] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[1] == 1:
        msg = msg + "L"
    elif status[1] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[2] == 1:
        msg = msg + "L"
    elif status[2] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[3] == 1:
        msg = msg + "L"
    elif status[3] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[4] == 1:
        msg = msg + "L"
    elif status[4] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    if status[5] == 1:
        msg = msg + "L"
    elif status[5] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    msg = msg + users
    print(msg)
    return msg

async def read(websocket, path):
    """
    With message from a web socket client, this function is called and will parse the message to determine the desired action:
    lock, unlock, or refresh. 
    """
    request = await websocket.recv()
    msg = ""
    if(request[:4] == "lock"):
        reference = request[4:7]
        user = request[7:]
        name = get_names(reference)
        msg = lock(name,user)
    elif(request[:4] == "unlk"):
        reference = request[4:7]
        user = request[7:]
        name = get_names(reference)
        msg = unlock(name,user)
    elif(request[:4] == "refr"):
        msg = refresh()
    await websocket.send(msg)

start_server = websockets.serve(read, "128.187.57.231", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()