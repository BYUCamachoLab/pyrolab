import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, NamedTuple, Union

import appnope
import Pyro5.api as api
from pydantic import BaseModel
from tabulate import tabulate

from pyrolab import PYROLAB_DATA_DIR
from pyrolab.manager import ProcessManager
from pyrolab.configure import DaemonConfiguration, GlobalConfiguration, NameServerConfiguration, ServiceConfiguration, update_config, reset_config, export_config


log = logging.getLogger(__name__)
appnope.nope()


INSTANCE_DATA = PYROLAB_DATA_DIR / "instance"
INSTANCE_DATA.mkdir(parents=True, exist_ok=True)
LOCKFILE = INSTANCE_DATA / "pyrolabd.lock"


class InstanceInfo(BaseModel):
    pid: int
    uri: str


class PSInfo(NamedTuple):
    name: str
    ptype: str
    created: datetime
    status: str
    uri: str


def parse_process(process) -> Dict[str, Any]:
    if process:
        created = process.created
        if datetime.now() - created > timedelta(seconds=86400):
            days = (datetime.now() - created).seconds / 86400
            status = f"Up {int(days)} hours"
        elif datetime.now() - created > timedelta(seconds=3600):
            hrs = (datetime.now() - created).seconds / 3600
            status = f"Up {int(hrs)} hours"
        elif datetime.now() - created > timedelta(seconds=120):
            mins = (datetime.now() - created).seconds / 60
            status = f"Up {int(mins)} minutes"
        elif datetime.now() - created > timedelta(seconds=60):
            status = f"Up 1 minute"
        else:
            status = f"Up {(datetime.now() - created).seconds} seconds"
        uri = ""
        created = created.strftime("%Y-%m-%d %H:%M:%S")
    else:
        created = ""
        status = "Stopped"
        uri = ""
    return {"created": created, "status": status, "uri": uri}


@api.expose
@api.behavior(instance_mode="single")
class PyroLabDaemon:
    def __init__(self):
        print(f"launching {id(self)} running at {os.getpid()}")
        self.manager = ProcessManager.instance()
        GlobalConfiguration.instance().load_config()

    def whoami(self):
        return f"{id(self)} at {os.getpid()}"

    def ps(self):
        """
        List all known processes grouped as nameservers, daemons, and services.

        Lists process names, status (i.e. running, stopped, etc.), start time,
        URI/ports, etc.
        """
        plc = GlobalConfiguration.instance().get_config()
        listing = []
        for ns in plc.nameservers.keys():
            process = self.manager.get_nameserver_process(ns)
            results = parse_process(process)
            listing.append(PSInfo(ns, "nameserver", **results))
        for daemon in plc.daemons.keys():
            process = self.manager.get_daemon_process(daemon)
            results = parse_process(process)
            listing.append(PSInfo(daemon, "daemon", **results))
        for service in plc.services.keys():
            listing.append(PSInfo(service, "service", "", "", ""))
        
        return tabulate(listing, headers=["NAME", "TYPE", "CREATED", "STATUS", "URI"])

    def config_update(self, filename: Union[str, Path]):
        return update_config(filename)

    def config_reset(self):
        return reset_config()

    def config_export(self, filename: Union[str, Path]):
        return export_config(filename)

    def start_ns(self, nameserver: str):
        self.manager.launch_nameserver(nameserver)

    def start_daemon(self, daemon: str):
        self.manager.launch_daemon(daemon)

    def start_service(self, service: str):
        pass

    def stop_ns(self, nameserver: str):
        self.manager.stop_nameserver(nameserver)

    def stop_daemon(self, daemon: str):
        self.manager.stop_daemon(daemon)

    def stop_service(self, service: str):
        pass

    def info(self, name: str):
        pass

    def logs(self, name: str):
        pass

    def rename_nameserver(self, old_name: str, new_name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if old_name in GLOBAL_CONFIG.get_config().nameservers:
            config = GLOBAL_CONFIG.get_config().nameservers[old_name]
            del GLOBAL_CONFIG.get_config().nameservers[old_name]
            GLOBAL_CONFIG.get_config().nameservers[new_name] = config
            GLOBAL_CONFIG.save_config()

    def rename_daemon(self, old_name: str, new_name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if old_name in GLOBAL_CONFIG.get_config().daemons:
            config = GLOBAL_CONFIG.get_config().daemons[old_name]
            del GLOBAL_CONFIG.get_config().daemons[old_name]
            GLOBAL_CONFIG.get_config().daemons[new_name] = config
            GLOBAL_CONFIG.save_config()

    def rename_service(self, old_name: str, new_name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if old_name in GLOBAL_CONFIG.get_config().services:
            config = GLOBAL_CONFIG.get_config().services[old_name]
            del GLOBAL_CONFIG.get_config().services[old_name]
            GLOBAL_CONFIG.get_config().services[new_name] = config
            GLOBAL_CONFIG.save_config()

    def restart_nameserver(self, name: str):
        pass

    def restart_daemon(self, name: str):
        pass

    def restart_service(self, name: str):
        pass

    def add_nameserver(self, name: str, config: NameServerConfiguration):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name not in GLOBAL_CONFIG.get_config().nameservers:
            GLOBAL_CONFIG.get_config().nameservers[name] = config
            GLOBAL_CONFIG.save_config()

    def rm_nameserver(self, name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name in GLOBAL_CONFIG.get_config().nameservers:
            del GLOBAL_CONFIG.get_config().nameservers[name]
            GLOBAL_CONFIG.save_config()

    def add_daemon(self, name: str, config: DaemonConfiguration):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name not in GLOBAL_CONFIG.get_config().daemons:
            GLOBAL_CONFIG.get_config().daemons[name] = config
            GLOBAL_CONFIG.save_config()

    def rm_daemon(self, name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name in GLOBAL_CONFIG.get_config().daemons:
            del GLOBAL_CONFIG.get_config().daemons[name]
            GLOBAL_CONFIG.save_config()

    def add_service(self, name: str, config: ServiceConfiguration):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name not in GLOBAL_CONFIG.get_config().services:
            GLOBAL_CONFIG.get_config().services[name] = config
            GLOBAL_CONFIG.save_config()

    def rm_service(self, name: str):
        GLOBAL_CONFIG = GlobalConfiguration.instance()
        if name in GLOBAL_CONFIG.get_config().services:
            del GLOBAL_CONFIG.get_config().services[name]
            GLOBAL_CONFIG.save_config()

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
            ii = InstanceInfo(pid=os.getpid(), uri=str(uri))
            with LOCKFILE.open("w") as f:
                f.write(ii.json())
            daemon.requestLoop()
        finally:
            LOCKFILE.unlink()
