# Introduction

pynet is a set of tools acting like proxys. It is composed for now as 3 tools:
- pycat which is a socat like tool
- pyproxy which allows you to established proxy
- pytun that is used to create Ethernet/IP tunnels

Many times I need to MiTM a network communication and I often use socat. But as soon as you need more than only forward the communication, socat is quite limited. So I developped pycat that acts as socat, but it comes with easily developpable modules that are called between endpoints, to read, store or modify the communication.

# TODO
- Improve code handling command line that is REALLY ugly
- Fix bugs
- Fix others bugs
