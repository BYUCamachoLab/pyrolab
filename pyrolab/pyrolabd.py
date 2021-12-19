import os
import pathlib
import logging

import appnope
import Pyro5.api as api
from pydantic import BaseModel
from tabulate import tabulate

from pyrolab import PYROLAB_DATA_DIR
from pyrolab.manager import ProcessManager


log = logging.getLogger(__name__)
appnope.nope()


INSTANCE_DATA = PYROLAB_DATA_DIR / "instance"
INSTANCE_DATA.mkdir(parents=True, exist_ok=True)
LOCKFILE = INSTANCE_DATA / "pyrolabd.lock"


class InstanceInfo(BaseModel):
    pid: int
    uri: str


@api.expose
@api.behavior(instance_mode="single")
class PyroLabDaemon:
    def __init__(self):
        print(f"launching {id(self)} running at {os.getpid()}")
        self.manager = ProcessManager.instance()

    def whoami(self):
        return f"{id(self)} at {os.getpid()}"

    def ps(self):
        table = [["Sun",696000,1989100000],["Earth",6371,5973.6],["Moon",1737,73.5],["Mars",3390,641.85]]
        return tabulate(table, headers=["PLANET","R (km)", "MASS (x 10^29 kg)"])

    def config(self):
        pass

    @api.oneway
    def shutdown(self):
        print("shutting down")
        self._pyroDaemon.shutdown()


if __name__ == "__main__":
    if LOCKFILE.exists():
        raise RuntimeError(f"Lockfile already exists. Is another instance running?")
    else:
        try:
            LOCKFILE.touch(exist_ok=False)
            daemon = api.Daemon()
            pyrolabd = PyroLabDaemon()
            uri = daemon.register(pyrolabd, "pyrolabd")
            print(uri)
            ii = InstanceInfo(pid=os.getpid(), uri=str(uri))
            with LOCKFILE.open("w") as f:
                f.write(ii.json())
            daemon.requestLoop()
        finally:
            LOCKFILE.unlink()
