# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
server
------

Implementation of an Daemon servers that are 2-way SSL capable.
"""

import Pyro5.api
from cryptography import x509
from cryptography.hazmat.backends import default_backend

import pyrolab
import pyrolab.errors


class Daemon(Pyro5.api.Daemon):
    """
    Simple wrapper around ``Pyro5.api.Daemon``.
    """
    pass


class CertValidatingDaemon(Daemon):
    def validateHandshake(self, conn, data):
        """
        Validate the certificate received from a connecting client.

        Requires that the configuration attribute ``SSL_CACERTS`` points to
        the public key certificate of the connecting client.

        Raises
        ------
        pyrolab.errors.CommunicationError
            If any of the certificate attributes do not match the expected
            values.
        """
        if not pyrolab.config.SSL:
            raise pyrolab.errors.CommunicationError("SSL disabled, cannot use CertValidatingDaemon")

        cert = conn.getpeercert()
        if not cert:
            raise pyrolab.errors.CommunicationError("client certificate missing")

        allowed_cert = x509.load_pem_x509_certificate(open(pyrolab.config.SSL_CACERTS, 'rb').read(), default_backend())
        if int(cert["serialNumber"], 16) != allowed_cert.serial_number:
            raise pyrolab.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])
        
        subject = dict(p[0] for p in cert["subject"])
        if subject["countryName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value:
            raise pyrolab.errors.CommunicationError("certificate country does not match")
        if subject["organizationName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value:
            raise pyrolab.errors.CommunicationError("certitifcate organization does not match")

        return super().validateHandshake(conn, data)


expose = Pyro5.api.expose
