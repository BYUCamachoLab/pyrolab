import asyncio
import websockets
from pyrolab.api import locate_ns, Proxy

def getNames(reference):
    names = []
    if(reference == "TSL"):
        names = ["lasers.TSL550"]
    elif(reference == "PPC"):
        names = ["PPCL550"]
    elif(reference == "PP2"):
        names = ["PPCL551"]
    elif(reference == "MIC"):
        names = ["UC480"]
    elif(reference == "LAM"):
        names = ["LAMP"]
    elif(reference == "KCU"):
        names = ["KCUBE_ROT","KCUBE_LAT","KCUBE_LON"]
    return names

def get_status(name):
    valid = True
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
        valid = False
        return -1

def lock(names):
    try:
        for name in names:
            ns = locate_ns(host="camacholab.ee.byu.edu")
            service = Proxy(ns.lookup(name))
            service.lock()
            service._pyroRelease()
        return "LOCKED"
    except(Pyro5.errors.NamingError):  
        return "UNLOCKED"

def unlock(names):
    try:
        for name in names:
            ns = locate_ns(host="camacholab.ee.byu.edu")
            service = Proxy(ns.lookup(name))
            service.release()
            service._pyroRelease()
        return "UNLOCKED"
    except(Pyro5.errors.NamingError):
        return "LOCKED"

def refresh():
    names = ["lasers.TCL550","PPCL550","PPCL551","UC480","LAMP","KCUBE_ROT","KCUBE_LAT","KCUBE_LON"]
    status = []
    for name in names:
        s = get_status(name)
        status.append(s)
    msg = ""
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
    if status[5] == 1 and status[6] == 1 and status[7] == 1:
        msg = msg + "L"
    elif status[5] == 0 and status[6] == 0 and status[7] == 0:
        msg = msg + "U"
    else:
        msg = msg + "-"
    return msg

async def read(websocket, path):
    request = await websocket.recv()
    msg = ""

    if(request[:4] == "lock"):
        reference = request[4:]
        names = getNames(reference)
        for name in names:
            msg = lock(name)
    elif(request[:4] == "unlk"):
        reference = request[4:]
        names = getNames(reference)
        for name in names:
            msg = unlock(name)
    elif(request[:4] == "refr"):
        msg = refresh()
    
    await websocket.send(msg)

start_server = websockets.serve(read, "10.32.112.191", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()