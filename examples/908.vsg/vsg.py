import time
from pyrolab.drivers.function_generators.smcv100b import SMCV100B

function_generator_ip = "10.32.112.163"

fungen = SMCV100B()

fungen.connect(function_generator_ip)
fungen.set_freq(1e8)
fungen.set_amp(4)
fungen.set_phase(180)
fungen.turn_on()
fungen.sweep_freq_lin(1e8, 1e9, 1e6, 10e-3)
fungen.shut_down()
fungen.close()
