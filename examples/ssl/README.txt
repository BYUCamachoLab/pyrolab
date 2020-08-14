SSL example showing how to use PyroLab's 2-way-SSL Proxy clients.

What this means is that the server has a certificate, and the client as well.
The server only accepts connections from clients that provide the proper certificate
(and, of course, clients only connect to servers having a proper certificate).

This example uses the self-signed demo certs that come with PyroLab, so in the code
you'll also see that we configure the SSL_CACERTS so that SSL will accept the self-signed
certificate as a valid cert.



If the connection is successfully established, all communication is then encrypted and secure.