from pyrolab.drivers.motion import bpc303 as bp

good = bp.start()
if good == 1:
    bp.zero_all()
    p = bp.get_pos(1)
    print(p)
    bp.home()
    #bp.move_to(20000,20000,20000)
    bp.set_home(5000,10000,5000)
    bp.home()
    x,y,z = bp.get_all()
    print("Point: (", x, ",", y, ",", z, ")")
    for i in range(10):
        bp.jog_all(i*10,i*10,i*10)
        x,y,z = bp.get_all()
        print("Point: (", x, ",", y, ",", z, ")")
    bp.move_to(5000,5000,5000)
    x,y,z = bp.get_all()
    p = bp.get_pos(1)
    print(p)
    print("Point: (", x, ",", y, ",", z, ")")
    disconnected = bp.end()
    if disconnected == 0:
        print("Could not disconnect")
else:
    print("Could not find device")