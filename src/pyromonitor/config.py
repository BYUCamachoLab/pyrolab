from omegaconf import OmegaConf

from pyromonitor import CONFIG_FILE


_defaultcfg = {
    "host": "localhost",
    "port": 8080,
    "nameserver": "localhost",
    "ns_port": 9090,
    "polling": 300,
}


CONFIG = OmegaConf.create(_defaultcfg)
if CONFIG_FILE.exists():
    userconf = OmegaConf.load(CONFIG_FILE)
    CONFIG.merge_with(userconf)
