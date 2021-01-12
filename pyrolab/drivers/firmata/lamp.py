import pyfirmata
import time

board = pyfirmata.Arduino('COM5')

while True:
    board.digital[13].write(1)
    time.sleep(20)
    board.digital[13].write(0)
    time.sleep(5)