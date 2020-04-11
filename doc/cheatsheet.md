# pycat

## Send input standard to a program

   pycat TCP-LISTEN -p 1337 Exec -c "ssh user@server"

## Send command to an SSH Server

   pycat - SSH -d ip -U user -P password

## Reading Unix socket

   pycat UNIX-LISTEN -b /tmp/test_unix UNIX-CONNECT -d /tmp/ssh-QknJmQenOy19/agent.27601  Logger	

## Basic MiTM in a SSH communication

   pycat SSH_LISTEN -p 2222 -d ip -U user -P password Logger -H

- Only basic MiTM can be done using this mechanism, for example Agent forwarding won't work. You have to use SSHProxy instead

# pyproxy

## TCP Proxy use cases

-  Forward data from port localhost port 1337 to ip port 1338 and display data

   pyproxy TCPProxy -p 1337 --server-ip ip --server-port 1338 Logger

## UDP Proxy use cases

- Forward data from port localhost port 1337 to ip port 1338 using the same source port (--mirror) as the client connecting to port 1337

   pyproxy UDProxy -p 1337 --server-ip ip --server-port 1338 --mirror

## TLS Proxy use cases

- Decrypt SSL/TLS communication (of course, certificate needs to be allowed on the client)

   pyproxy TLSProxy -p 1337 --server-port 1338 -c cert.pem -k key.pem Logger -H

- Perform 10% of bits corruption in the payload embeded in the SSL/TLS communication

  pyproxy TLSProxy -p 1337 --server-port 1338 -c cert.pem -k key.pem Corrupt --both -n 10

## SSH Proxy use cases

- MiTM SSH communication

    pyproxy SSHProxy -p 2222 --server-ip ip --server-port 22 -U user Logger -H

- TODO: command sent in an exec_command channel won't be seen inside the module Logger...

# pytun

## Create a TCP tunnel to embeds IP traffic between IP_a and IP_b

On host IP_a:

   pytun -i 192.168.64.1 TCP -d IP_b -p 8443

It will create a tun0 interface with IP 102.168.64.1. Everything sends to this IP will be tunnelled inside the TCP tunnel established on port 8443 between IP_a and IP_b.

On Host IP_b:
   pytun -s -i 192.168.64.2 TCP-LISTEN -p 8443
