http://xapi-project.github.io/xen-api/usage.html

https://fontawesome.com/icons?d=gallery&m=free
boxes
cloud
cloud-meatball
cubes
grip-horizontal
grip-vertical
layer-group
network-wired
project-diagram
servcer
sitemap
stream
tasks
th
th-large
th-list
whmcs
A cause de https://github.com/xapi-project/xen-api/issues/2100 je fourni une version recente de XenAPI
qui necessite six.py.

http://140995-r630.dev.lab.s1.p.fti.net:8080/
https://docs.netdata.cloud/collectors/#netdata-plugins


test :
/opt/netdata/usr/libexec/netdata/plugins.d/python.d.plugin xenserver debug trace


Add server certificate to the trust store
=========================================

https://srkcitrix.wordpress.com/2012/06/11/replacing-the-default-xenserver-ssl-certificate/

.. code-block:: bash

   </etc/xensource/xapi-ssl.pem \
      sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' \
      > /etc/pki/ca-trust/source/anchors/$(hostname -f).crt
   update-ca-trust

