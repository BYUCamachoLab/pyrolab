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

class CertValidatingDaemon(Pyro5.api.Daemon):
    def validateHandshake(self, conn, data):
        cert = conn.getpeercert()
        if not cert:
            raise Pyro5.errors.CommunicationError("client certificate missing")

        # if cert["serialNumber"] != "076DC0606C84276E2D7D2850B83C99750A3A7EF6":
        if cert["serialNumber"] != "363D1BBA4ABC0CB4BE819E35A149390A522A854E":
            raise Pyro5.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])
        issuer = dict(p[0] for p in cert["issuer"])
        subject = dict(p[0] for p in cert["subject"])
        if issuer["organizationName"] != "CamachoLab":
            # issuer is not often relevant I guess, but just to show that you have the data
            raise Pyro5.errors.CommunicationError("cert not issued by CamachoLab")
        if subject["countryName"] != "US":
            raise Pyro5.errors.CommunicationError("cert not for country US")
        if subject["organizationName"] != "CamachoLab":
            raise Pyro5.errors.CommunicationError("cert not for CamachoLab")
        print("(SSL client cert is ok: serial={ser}, subject={subj})"
              .format(ser=cert["serialNumber"], subj=subject["organizationName"]))
        return super(CertValidatingDaemon, self).validateHandshake(conn, data)
