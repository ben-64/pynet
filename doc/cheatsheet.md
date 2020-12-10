# pycat

## Send input standard to a program

```bash
pycat TCP-LISTEN -p 1337 Exec -c "ssh user@server"
```

## Send command to an SSH Server

```bash
pycat - SSH -d ip -U user -P password
```

## Reading Unix socket

```bash
pycat UNIX-LISTEN -b /tmp/test_unix UNIX-CONNECT -d /tmp/ssh-QknJmQenOy19/agent.27601  Logger	
```

## Basic MiTM in a SSH communication

```bash
pycat SSH_LISTEN -p 2222 -d ip -U user -P password Logger -H
```
 
- Only basic MiTM can be done using this mechanism, for example Agent forwarding won't work. You have to use SSHProxy instead

## Socks

### SocksClient

- It has to be used when you want to connect to a SOCKS server. Therefore you need to specify, the SOCKS server, and the final destination

```bash
pycat TCP-LISTEN -p 64240 SocksClient -d socks_ip -p socks-port -D final_ip -P final_port
```

### SocksServer

- It is like a SOCKS server, this endpoint is supposed to receive SOCKS protocol, so dynamically it will connect to the server specified in the SOCKS protocol

```bash
pycat TCP-LISTEN -p 64240 SocksServer
```

## Etherpuppet

- It is possible to get a kind of poor [etherpuppet](https://github.com/secdev/etherpuppet). The goal is to duplicate an ethernet card existing on a machin on another one. For serious purposes, I encourage you to prefer etherpuppet.

On the server where the real card exists :

```bash
pycat UDP-LISTEN -p 64240 Interface -i eth0 --bpf ip_client:64240
```

The `BPF` filter is important to avoid sending the UDP communication as well inside itself, leading to an infinite loop. The `BPF` filter resulting will be `not ((dst host ip_client and src port 64240) or (src host ip_client and dst port 64240))`.

Every packet read on `eth0` will be sent in UDP, and every packet read on UDP will be sent to `eth0`.

On the client where you want to see the same card:

```bash
pycat TAP -i pytap0 UDP -d server_ip -p 64240
```

This command will create a `pytap0` interface on the client. As previously, every packet read from UDP will be sent to `pytap0` and every packet read on `pytap0` will be sent with UDP.
This allows to sniff on `pytap0` as we were directly on the server. At the same time, it is possible to send traffic to this network interface and it will be sent on the first system.

You have to configure this interface `pytap0` is you want to use it for other purposes than sniffing. Many problems can occur:
- If you want to have the exact same IP adress, the UDP commication will probably be cut off, because your system will try to go through this virtual interace to reach the server and not anymore through the classical routing. It will happen if the interface you want to dupicate is the same at the one that receive the UDP communication. You can solve this problem by using iproute2 advanced routing (for example by using a different routing table for this UDP port) or by using a different Linux network namespace
- If you want to get a different MAC address, be sure to set `eth0` in promiscous mode (by using the `--promisc` option). Otherwise, you won't see any traffic destinated to your MAC, because `eth0` won't see it. Be sure to use a different IP address, because some nasty things could happen (multiple MAC for the same IP).
- If you want to use the same MAC address and the same IP Adress, be sure to block traffic the outgoing traffic on the server, otherwise you will open communication, than the server itself will cut, because it never opened it.

### TCP Tunnel

Be careful, if you use a SOCK_STREAM oriented protocol, such as TCP, you may have some troubles, because network interfaces are datgram oriented. It means that some datagrams can be splitted, or merged before being sent to the interface.
You should use the `LengthProto` using `--proto` option for such endpoints. Every datagram will be prefixed by its length and this length will be removed by the orther endpoing ensuring that datagram are not splitted/merged. You can find more information about protocols [here](proto.md).

```bash
pycat TCP-LISTEN --proto "LengthProto()" -p 64240 Interface -i eth0 --bpf ip_client:64240
pycat TAP -i pytap0 TCP --proto "LengthProto()" -d server_ip -p 64240
```


# pyproxy

## TCP Proxy use cases

-  Forward data from port localhost port 1337 to ip port 1338 and display data

```bash
pyproxy TCPProxy -p 1337 --server-ip ip --server-port 1338 Logger
```

## UDP Proxy use cases

- Forward data from port localhost port 1337 to ip port 1338 using the same source port (--mirror) as the client connecting to port 1337

```bash
pyproxy UDProxy -p 1337 --server-ip ip --server-port 1338 --mirror
```

## TLS Proxy use cases

- Decrypt SSL/TLS communication (of course, certificate needs to be allowed on the client)

```bash
pyproxy TLSProxy -p 1337 --server-port 1338 -c cert.pem -k key.pem Logger -H
```

- Perform 10% of bits corruption in the payload embeded in the SSL/TLS communication

```bash
pyproxy TLSProxy -p 1337 --server-port 1338 -c cert.pem -k key.pem Corrupt --both -n 10
```

## SSH Proxy use cases

- MiTM SSH communication

```bash
pyproxy SSHProxy -p 2222 --server-ip ip --server-port 22 -U user Logger -H
```

- TODO: command sent in an exec_command channel won't be seen inside the module Logger...

# pytun

## Create a TCP tunnel to embeds IP traffic between IP_a and IP_b

On host IP_a:

```bash
pytun -a 192.168.64.1 TCP -d IP_b -p 8443
```

It will create a tun0 interface with IP 102.168.64.1. Everything sends to this IP will be tunnelled inside the TCP tunnel established on port 8443 between IP_a and IP_b.

On Host IP_b:

```bash
pytun -s -a 192.168.64.2 TCP-LISTEN -p 8443
```
