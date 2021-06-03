"""
Note that ``ns_profile`` is a global profile object and is intended to be a 
Singleton.
"""

from .nameserver import start_ns_loop, start_ns
from .configure import ns_profile, NameserverConfiguration
from .configure import NAMESERVER_CONFIG_DIR, NAMESERVER_DATA_DIR

__all__ = [
    "start_ns_loop",
    "start_ns",
    "ns_profile",
    "NameserverConfiguration",
]
