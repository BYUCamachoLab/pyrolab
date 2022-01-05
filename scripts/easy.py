from Pyro5 import config
from Pyro5.api import serve

from pyrolab.drivers.cameras.uc480 import UC480


config.NS_HOST = "camacholab.ee.byu.edu"
config.NS_PORT = 9090

# serialno: 4103247225
serve(
    {
        "uc480": UC480,
    },
    use_ns=True,
)
