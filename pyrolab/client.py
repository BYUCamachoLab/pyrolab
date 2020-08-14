# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Client
------

Implementation of Proxy clients that are 2-way SSL capable.
"""

import Pyro5.api
from cryptography import x509
from cryptography.hazmat.backends import default_backend

import pyrolab
import pyrolab.errors


class Proxy(Pyro5.api.Proxy):
    """
    Simple wrapper around ``Pyro5.api.Daemon``.
    """
    pass


class CertCheckingProxy(Proxy):
    """
    A certificate cross-referencing Proxy.

    This Proxy ensures that the certificate from the server matches the
    expected certificate. The configuration setting for ``SSL_CACERTS`` must
    be set to point to the public key of the server's certificate.
    """
    def _pyroValidateHandshake(self, response):
        """
        Cross references the received certificate with the expected 
        certificate from a given server.
        """
        if not pyrolab.config.SSL:
            raise pyrolab.errors.CommunicationError("SSL disabled, cannot use CertCheckingProxy")

        cert = self._pyroConnection.getpeercert()
        verify_cert(cert)


def verify_cert(cert):
    """
    Cross references the certificate with the one defined in the configuration
    attribute ``SSL_CACERTS``.

    Parameters
    ----------
    cert
        The certificate received from the server over the network.

    Raises
    ------
    pyrolab.errors.CommunicationError
        If any attribute of the certificate doesn't match.
    """
    if not cert:
        raise pyrolab.errors.CommunicationError("cert missing")

    allowed_cert = x509.load_pem_x509_certificate(open(pyrolab.config.SSL_CACERTS, 'rb').read(), default_backend())
    if int(cert["serialNumber"], 16) != allowed_cert.serial_number:
        raise pyrolab.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])

    subject = dict(p[0] for p in cert["subject"])
    if subject["countryName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value:
        raise pyrolab.errors.CommunicationError("certificate country does not match")
    if subject["organizationName"] != allowed_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value:
        raise pyrolab.errors.CommunicationError("certitifcate organization does not match")
