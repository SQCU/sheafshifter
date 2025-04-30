#pyenet_conncalib.py
import enet
import sys, os
import time
import math

#theres more tedious sysadmin crimes to account for
#this time it's: MTU validation and packet sharding
# HERMENEUTICS OF SYSADMIN DISTRUST:
# OUTER AND INNER HEADER
# outer header: enet.packet(data, flags)
# compose flags by list(flags)
# def compose(list)
#   carrier = int(0)
#   for fl in list:
#       bitwise_OR(carrier,fl)
#   return carrier
# noteworthy enet flags: 
# ENET_PACKET_FLAG_UNSEQUENCED
#   disable the packet ordering inhibitors
#   this is a Good Thing if ur writing ur own headers
# ENET_PACKET_FLAG_UNRELIABLE_FRAGMENT
#   enet will try to automatically fragment mtu-breaking packets
#   quick skim didn't actually tell us how mtu is discovered tho

def compose_bflags(list):
    carrier = int(0)
    for fl in list:
        carrier|fl
    return carrier

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
    rcounter = 0
    tcounter = 0
    tinit = 0.250
    run = True
    syn = False
    synack = False
    shutdown_sent = False


    pflags = compose_bflags(
        [enet.PACKET_FLAG_UNSEQUENCED,
        enet.PACKET_FLAG_UNRELIABLE_FRAGMENT]
        )
    
    #sample data:
    with open("./notes/1bit_redraw.png", "rb") as image_file:
        image_bytes = image_file.read()

    print(f"expect 4496: {len(image_bytes)}")
    

    while run:
        event = host.service(0) #if dialed too low... can't send shutdown message?
        
        if event.type == enet.EVENT_TYPE_CONNECT:
            print("%s: CONNECT" % event.peer.address)
            synack = True
            continue
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            print("%s: DISCONNECT" % event.peer.address)
            run = False
            continue
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            print("%s: IN:  %r" % (event.peer.address, event.packet.data[:32]))
            synack = True
            rcounter+=1
            if event.packet.data == b"SHUTDOWN":
                #wow this block is *really important* for removing race conditions.
                peer.disconnect_later()
            continue
        
        if not syn and not synack:
            seed_msg = bytes(00000000)
            packet = enet.Packet(seed_msg, pflags)
            peer.send(0, packet)
            syn = True
            continue
        elif not synack:
            tstep = tinit * math.log(abs(math.e+tcounter)) **2
            #perfectly ordinary easing function don't think about it
            print(f"sleep tstep:{tstep}sec")
            time.sleep(tstep)
            tcounter+=tstep
            if tcounter>=60:
                print(f"sleeping 60 seconds is too long. timing out~")
                run = False
                break
            continue
            
        if not shutdown_sent and synack:
            seed_msg = image_bytes
            packet = enet.Packet(seed_msg, pflags)
            peer.send(0, packet)

            print("%s: OUT: %r" % (peer.address, seed_msg[:32]))
            counter += 1
    
        if counter>=1 and not shutdown_sent:
            #see if packet gets fragmented!
            msg = SHUTDOWN_MSG
            peer.send(0, enet.Packet(msg))
            shutdown_sent = True

        """
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
        """

    print(f"counter:{counter};rcounter:{rcounter}")
    print(f"total stalled time:{tcounter}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)