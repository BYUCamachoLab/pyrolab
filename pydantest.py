from pathlib import Path
from pyrolab.configure import NameServerSettings, PyroLabConfiguration, ServiceSettings

plc = PyroLabConfiguration(
    nameservers={
        "default": NameServerSettings(host="public"),
        "local": NameServerSettings(host="localhost"),
        "remote": NameServerSettings(host="remotehost"),
    },
    services={
        "wanda": ServiceSettings(module="pyrolab", classname="billy"),
        "vision": ServiceSettings(module="pyrolab", classname="billy", daemon="remotehost"),
        "westview": ServiceSettings(module="pyrolab", classname="billy", daemon="public"),
    }
)

data = plc.yaml()
print(data)

tempfile = Path("./temp.yaml")
with tempfile.open("w") as f:
    f.write(data)

plc2 = PyroLabConfiguration.read_config_file(tempfile)
print(plc2.yaml())
