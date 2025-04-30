#logging II:
#   http.server logging bridge.
#   a 'static http server' which does 2 things:
#serve /index, which is some html: typesetting rules, and some javascript.
#serve /events 
#   /events necessarily contains further resources: /events/{e_tID}
#we might thereafter use the javascript fetch API:
#
#   async function getData() {
#     const url = "https://mproc_serv.intra/events.json";
#       try {
#       const response = await fetch(url);
#     const json = await response.json();
#     console.log(json);
#       } catch (error) {
#       console.error(error.message);
#     }
#   }
#   (yes, the javascript fetch API is literally "http but if you could code it".)
#for obvious reasons, web media has to be passed as json for html to use it.
#its called hypertext markup language, not hypertext IPC language lol

import http
import msgspec

import enet
import sys, os
import math, time

#sure messagepack why not. lets us uh, lets us. pack message
#json decoding is probably faster than msgpack though

### event header semantics:
#   lets say we want an event to decode to:
# {header:{protocol:1, event:b"ADMIN", datalength:8}, data:b"SHUTDOWN"}
# event:b"ADMIN",datalength:len(b"PCKT:SHUTDOWN"))
#literally:
#+"b"+int4bitter(13) -> b"\x04"+b"b"+b"\r" -> bytearray with a length of 6.
#this freezes our protocol such that transmitted data cannot grow past 4.2 gigachars.
#this is very sad. :( we would have to version bump to v2 if we wanted a petabyte long packet :(((
#an enet frame capacity is probably at least 500 bytes btw.

#admin packets:
#for statuscode in set(b"SHUTDOWN",b"SYN",b"ACK",b"ECHO"):
#    header = vchar+event_2head(b"ADMIN")+int4bitter(len(statuscode))
#    body = statuscode   
#    think about making ACK package session status at the same time. great protocol v2 add right?
#    sheafshifter_packet = header+body

#decode admin packets:
#    header = packet[0:7]
#    body = packet[7:]
#    decdict = {
#    "version":intsweeten(header[0:1]),
#    "event":head_2event(header[1:2]),
#    "data_length":intsweeten(header[2:])
#    }

#logging packet:
    #logdata = sbytes(printable[0])+sbytes(printable[1])
    #do NOT fall for self-serialization. you'd have to communicate repr indices 
    #pckdata = msgspec.msgpack.encode(printable)
    #messagepack objects have valid lengths!
    #header = vchar+event_2head(b"LOGG")+int4bitter(len(pckdata))

    #header[0:1]:version, header[1:2]:event, header[2:]:data_length 


#(bytes(taskUUID), tuple(int,int,int), len(bytes(bulk)))

#i HATE bytes
def intbitter(inty):
    return int.to_bytes(inty,1,byteorder="big")
def int4bitter(inty):
    return int.to_bytes(inty,4,byteorder="big")
def intsweeten(inty):
    return int.from_bytes(inty,byteorder="big")
def byxor(lbys, rbys):
    return bytes([lby^rby for lby, rby in zip(lbys, rbys) ])
def sbytes(stringy):
    return bytes(stringy, 'utf8')
def strytes(bystrng):
    return stringy.decode('utf8')



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

    # sheafshifter_proto_1
    msgpack_encoder = msgspec.msgpack.Encoder()
    msgpack_decoder = msgspec.msgpack.Decoder()
    #packetization 
    protocol_version = 1
    event_2head = {b"LOGG":b"a",
    b"ADMIN":b"b",
    b"DATA":b"c"}
    head_2event = {b"a":b"LOGG",
    b"b":b"ADMIN",
    b"c":b"DATA"}
    statuscodes = (b"SHUTDOWN", b"SYN", b"ACK", b"ECHO",b"MIRRORSYN")
    vchar = intbitter(protocol_version*4)

        #proto1 functions
    def a_encode(event, statuscode):
        assert event in event_2head.keys()
        assert statuscode in statuscodes
        header = vchar+event_2head[event]+int4bitter(len(statuscode))
        return header + statuscode
    def shshp_peek(packet):
        assert len(packet)>=6   #proto 1
        assert intsweeten(packet[0])==4
        return head_2event[packet[1:2]] 
        #event, e.g. ADMIN, LOGG, DATA/
    def a_decode(packet, ecode):
        #header = packet[0:7]
        decdict = {
            "version":intsweeten(header[0:1]),
            "event":head_2event(header[1:2]),
            "data_length":intsweeten(header[2:7])
        }
        assert decdict["event"] == ecode
        assert decdict["data_length"] == len(packet)-6
        #all okay
        return decdict, packet[7:]
    def l_encode(event, printable):
        assert event in event_2head.keys()
        pckdata = msgpack_encoder.encode(printable)
        header = vchar+event_2head[event]+int4bitter(len(pckdata))
        return header+pckdata   
    def l_decode(packet, ecode):
        decdict = {
            "version":intsweeten(header[0:1]),
            "event":head_2event(header[1:2]),
            "data_length":intsweeten(header[2:7])
        }
        assert decdict["event"] == ecode
        assert decdict["data_length"] == len(packet)-6
        return decdict, msgpack_decoder.decode(packet[7:])

    
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
            print("%s: IN:  %r" % (event.peer.address, event.packet.data[:80]))
            synack = True
            rcounter+=1
            if event.packet.data == b"SHUTDOWN":
                #wow this block is *really important* for removing race conditions.
                peer.disconnect()
                break
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

        if not shutdown_sent and synack and counter<=1:
            shshp_data = a_encode(b"ADMIN",statuscodes[4])    #mirrorsyn
            #print(shshp_data)
            peer.send(0, enet.Packet(shshp_data, enet.PACKET_FLAG_RELIABLE))
            counter += 1
            continue
        elif counter>=1 and not shutdown_sent:
            tstep = tinit * math.log(abs(math.e+tcounter)) **2
            #perfectly ordinary easing function don't think about it
            print(f"sleep tstep:{tstep}sec")
            time.sleep(tstep)
            tcounter+=tstep
            if tcounter>=60:
                print(f"slept 60 seconds. honkshoo mimi protocol engaged~")
                msg = SHUTDOWN_MSG
                peer.send(0, enet.Packet(msg))
                shutdown_sent = True
                #run = False
            continue
        elif shutdown_sent:
            tstep = tinit * math.log(abs(math.e+tcounter)) **2
            #perfectly ordinary easing function don't think about it
            print(f"sleep tstep:{tstep}sec")
            time.sleep(tstep)
            tcounter+=tstep
            if tcounter>=600:
                print(f"if you've been asleep for ten minutes it's time to go to bed~")
                run = False
                break
            continue


    print(f"counter:{counter};rcounter:{rcounter}")
    print(f"total stalled time:{tcounter}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)