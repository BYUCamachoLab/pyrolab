import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Kinesis" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

from pyrolab.drivers.motion import bpc303 as bp

bp1 = bp.BPC303(serial=71874833)
bp1.help()

good = bp1.start()
if good == 1:
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
else:
    print("Could not find device")