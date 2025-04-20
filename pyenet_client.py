import enet
import sys, os

#complementary client to pyenet_serv.
#program subject to symbolic evolution optimization 
# (arbitrary lines of code added and removed until operational)
#towards zero-delay enet_host_service() polling
#   (in pyenet: enet.Host.service())
#without misdelivery, duplication, or dropped packets.

def barray_xor(barray,operand):
    result = bytearray()
    for i in range(len(barray)):
        result.append(barray[i] ^ operand)
    return result

def main():
    SHUTDOWN_MSG = b"SHUTDOWN"
    MSG_NUMBER = 10

    host = enet.Host(None, 1, 0, 0, 0)
    host.checksum = enet.ENET_CRC32
    peer = host.connect(enet.Address(b"localhost", 33333), 1)

    counter = 0
    run = True
    shutdown_sent = False

    while run:
        event = host.service(0) #if dialed too low... can't send shutdown message?
        if event.type == enet.EVENT_TYPE_CONNECT:
            print("%s: CONNECT" % event.peer.address)
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            print("%s: DISCONNECT" % event.peer.address)
            run = False
            continue
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            print("%s: IN:  %r" % (event.peer.address, event.packet.data))
            if event.packet.data == b"SHUTDOWN":
                #wow this block is *really important* for removing race conditions.
                peer.disconnect()
            continue

        if counter < MSG_NUMBER and not shutdown_sent:
            seed_msg = bytes(bytearray([i for i in range(40)]))
            msg = barray_xor(seed_msg, counter) #deterministic message varietizer
            packet = enet.Packet(msg)
            peer.send(0, packet)

            counter += 1
            print("%s: OUT: %r" % (peer.address, msg))
        if counter >= MSG_NUMBER and not shutdown_sent:
            msg = SHUTDOWN_MSG
            peer.send(0, enet.Packet(msg))
            shutdown_sent = True



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)