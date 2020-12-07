# Problematic

If we want to forward data from a datagram endpoint to another datagram endpoint, it may not work if there is a stream endpoint in the middle.
Stream endpoints may merge or split datagrams, and therefore it will not work. In order to solve this problem Protols have been added.
Right now, there are only two protocols:
- NoProto which obviously does not change anything to the data received/sent. It is the default protocol.
- LengthProto which adds a length value of the data sent for each datagram.

If you use LengthProto, you will be sure, that datagram packets won't be merged or splited.

```bash
# On the first system
$ pycat - TCP -p 64240 --proto "LengthProto()"

# On the second system
$ pycat TCP-LISTEN -p 64240 --proto "LengthProto()" -
```

Every packet written on the standard ouput of the first system will be preceeds by a length value by the TCP endpoint. This length value will be removed on the second system by the TCP-LISTEN endpoint. TCP-LISTEN will ensure that it sends to the standard output only full packets.
