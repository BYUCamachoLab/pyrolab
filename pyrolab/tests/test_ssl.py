

# import pytest

import Pyro5
import Pyro5.api

import pyrolab
from pyrolab.server import CertValidatingDaemon

Pyro5.config.SSL = True
Pyro5.config.SSL_REQUIRECLIENTCERT = True   # enable 2-way ssl
Pyro5.config.SSL_SERVERCERT = "../../certs/server_cert.pem"
Pyro5.config.SSL_SERVERKEY = "../../certs/server_key.pem"
Pyro5.config.SSL_CACERTS = "../../certs/client_cert.pem"    # to make ssl accept the self-signed client cert
print("SSL enabled (2-way).")

class Safe:
    @Pyro5.api.expose
    def echo(self, message):
        print("got message:", message)
        return "hi!"

def test_server():
    d = CertValidatingDaemon()
    uri = d.register(Safe)
    print("server uri:", uri)
    d.requestLoop()
