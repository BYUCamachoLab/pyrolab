from pyrolab.drivers.motion.z8xx import Z825B

linear = Z825B()
linear.connect(serialno="27003497", home=False)
try:
    while True:
        move_pos = int(input("Translation Position:"))
        if move_pos == 0:
            break
        pos = linear.get_position()
        print(f"Before Move: {pos}")
        linear.move_to(move_pos)
        pos = linear.get_position()
        print(f"After Move: {pos}")
    linear.move_to(0)
finally:
    linear.close()
