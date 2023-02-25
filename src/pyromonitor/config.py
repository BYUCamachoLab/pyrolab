from omegaconf import OmegaConf


_defaultcfg = {
    "nameserver": "camacholab.ee.byu.edu",
}

conf = OmegaConf.create(_defaultcfg)
