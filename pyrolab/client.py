# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
server
------

Implementation of an SSL enabled 2-way server.
"""

import Pyro5.errors
import Pyro5.api

import pyrolab

def verify_cert(cert):
    if not cert:
        raise Pyro5.errors.CommunicationError("cert missing")
    if cert["serialNumber"] != "363D1BBA4ABC0CB4BE819E35A149390A522A854E":
        raise Pyro5.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])

    subject = dict(p[0] for p in cert["subject"])

    if subject["countryName"] != "US":
        raise Pyro5.errors.CommunicationError("cert not for country NL")
    if subject["organizationName"] != "CamachoLab":
        raise Pyro5.errors.CommunicationError("cert not for CamachoLab")
    # print("(SSL server cert is ok: serial={ser}, subject={subj})"
    #       .format(ser=cert["serialNumber"], subj=subject["organizationName"]))

class CertCheckingProxy(Pyro5.api.Proxy):
    def _pyroValidateHandshake(self, response):
        cert = self._pyroConnection.getpeercert()
        verify_cert(cert)

def get_proxy(uri):
    if pyrolab.config.SSL:
        return CertCheckingProxy(uri)
    else:
        return Pyro5.api.Proxy(uri)
