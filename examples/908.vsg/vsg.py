import time
from pyrolab.drivers.function_generators.smcv100b import SMCV100B

function_generator_ip = "10.32.112.163"

fungen = SMCV100B()

fungen.connect(function_generator_ip)
fungen.set_freq(1e6)
fungen.set_amp(5)
fungen.turn_on()
fungen.sweep_freq_lin(1e6, 1e7, 1e6, 1)
time.sleep(5)
frequency = fungen.freq_running()
print(frequency)
fungen.close()

"""
Things to test:
- Frequency - works
- Amplitude - works
- Offest - works, but what does it actually do?
- Sweep - works
- Step up/down - works
- Shut down - works
- Running - don't know, where is the output?
- Reset sweeps - works

Stuff to write after that:
- Phase 
- Query the frequency sweeps?
"""
