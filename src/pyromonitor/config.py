from omegaconf import OmegaConf


_defaultcfg = {
    "nameserver": "camacholab.ee.byu.edu",
    "update_period": 300,
}

CONFIG = OmegaConf.create(_defaultcfg)
