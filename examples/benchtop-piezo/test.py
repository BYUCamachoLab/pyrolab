import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Kinesis" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

from pyrolab.drivers.motion import bpc303 as bp

# from win32event import CreateMutex
# from win32api import GetLastError
# from winerror import ERROR_ALREADY_EXISTS
# from sys import exit

# handle = CreateMutex(None, 1, 'David Service')

# if GetLastError() == ERROR_ALREADY_EXISTS:
#     # Take appropriate action, as this is the second instance of this script.
#     print('An instance of this application is already running.')
#     exit(1)

# from pyrolab.api import expose, locate_ns, Daemon, config, behavior

# def get_ip():
#     import socket
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.connect(("8.8.8.8", 80))
#     ip = s.getsockname()[0]
#     s.close()
#     return ip

# if __name__ == "__main__":
#     config.HOST = get_ip()
#     config.SERVERTYPE = "multiplex"
#     daemon = Daemon()
#     ns = locate_ns(host="camacholab.ee.byu.edu")

#     uri = daemon.register(BPC303)
#     ns.register("BPC303", uri)
#     try:
#         daemon.requestLoop()
#     finally:
#         ns.remove("BPC303")

bp1 = bp.BPC303("71874833")

#bp1.zero_all()
p = bp1.get_pos(1)
print(p)
bp1.home()
#bp.move_to(20000,20000,20000)
bp1.set_home(5000,10000,5000)
bp1.home()
x,y,z = bp1.get_all()
print("Point: (", x, ",", y, ",", z, ")")
for i in range(10):
    bp1.jog_all(i*10,i*10,i*10)
    x,y,z = bp1.get_all()
    print("Point: (", x, ",", y, ",", z, ")")
    bp1.fine_tune()
    x,y,z = bp1.get_all()
    print("F-Point: (", x, ",", y, ",", z, ")")
bp1.move_to(5000,5000,5000)
x,y,z = bp1.get_all()
p = bp1.get_pos(1)
print(p)
print("Point: (", x, ",", y, ",", z, ")")
disconnected = bp1.end()
if disconnected == 0:
    print("Could not disconnect")
