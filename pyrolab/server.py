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
from cryptography import x509
from cryptography.hazmat.backends import default_backend

import pyrolab
import pyrolab.errors


class CertValidatingDaemon(Pyro5.api.Daemon):
    def validateHandshake(self, conn, data):
        if not pyrolab.config.SSL:
            raise pyrolab.errors.CommunicationError("SSL disabled, cannot use CertValidatingDaemon")

        cert = conn.getpeercert()
        if not cert:
            raise pyrolab.errors.CommunicationError("client certificate missing")

        allowed_cert = x509.load_pem_x509_certificate(open(pyrolab.config.SSL_CACERTS, 'rb').read(), default_backend())
        if int(cert["serialNumber"], 16) != allowed_cert.serial_number:
            print('wrong cert')
            raise pyrolab.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])
        
        subject = dict(p[0] for p in cert["subject"])
        if subject["countryName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value:
            raise pyrolab.errors.CommunicationError("certificate country does not match")
        if subject["organizationName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value:
            raise pyrolab.errors.CommunicationError("certitifcate organization does not match")
        # print("(SSL client cert is ok: serial={ser}, subject={subj})"
        #       .format(ser=cert["serialNumber"], subj=subject["organizationName"]))
        return super().validateHandshake(conn, data)

def get_daemon():
    if pyrolab.config.SSL:
        return CertValidatingDaemon()
    else:
        return Pyro5.api.Daemon()
