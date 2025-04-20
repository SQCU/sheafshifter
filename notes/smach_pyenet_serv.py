#smach_pyenet_serv
import sys, os
import enet
from multiprocessing import Process, Queue
import threading

#empty project template doesn't have any control flow to keep enet host alive w.
#re: readme.md notes, 
#we need  control flow calling enet_host_service()
#to actually do anything with enet, incl. testing it

#okay we implemented a control circuit which takes a stream of bytearrays!
#last big mystery for the synchronous monoconnection program is the double print
#unconnecto /n unconnecto.
#mystery solved!

#new and scarier mystery: 
#how do we route control flow so that enet.Event & enet.Peer protected objects are never serialized?
#or how do we make those cython bindings... pickleable?

def enet_inbound(enethost, inqueue, outqueue, responses):
    run=True
    try:
        while run:
            event = enethost.service(0) # wait {operand} ms for network activity
            if event == enet.EVENT_TYPE_NONE:
                continue #it would be *really* weird to saturate queue with non-events!
            inqueue.put(event) #blocking i guess!!!
    except KeyboardInterrupt:
        run = False
        print("terminating enet in")

def enet_outbound(enethost, inqueue, outqueue, responses):
    run=True
    try:
        while run:
            sendable = outqueue.get()
            # sendable = (peer, channelID, packet)

            #sends and gets a return object
            sendstatus = sendable[0].send(sendable[1], sendable[2])
            if sendstatus == -1 :
                printstring = "%s: uh oh in the echo packeto" % event.peer.address
                responses.put(("printable",printstring))
                continue
            printstring = "%s: chn:%s out: %r" % (sendable[0].address, sendable[1], sendable[2])
            responses.put(("printable",printstring))
    except KeyboardInterrupt:
        run = False
        print("terminating enet out")

def blocky_printer(responses):
    run=True
    try:
        while run:
            printable = responses.get()
            print(printable[1])
            #weird, right?
            #the hypothesis here is that queue access is intrinsically cheaper than stdout
            #this is imaginable bc like. queue should move at cpu speed.
            #and cpus are very very fast.
    except KeyboardInterrupt:
        run = False
        print("terminating printer")

def echo_protocol(inqueue, outqueue, responses):
    connect_count = 0
    run = True
    shutdown_recv = False
    try:
        while run:
            event = inqueue.get() #blocks until something is queued. 
            #unblocked bc something was in that queue!
            if event.type == enet.EVENT_TYPE_CONNECT:
                printstring ="%s: connecto" % event.peer.address
                responses.put(("printable",printstring))
                connect_count +=1

            elif event.type == enet.EVENT_TYPE_DISCONNECT:
                printstring ="%s: unconnecto" % event.peer.address
                responses.put(("printable",printstring))
                connect_count -=1

                if connect_count <= 0 and shutdown_recv:
                    printstring = "%s remaining sessions" % connect_count
                    responses.put(("printable",printstring))
                    run = False

            elif event.type == enet.EVENT_TYPE_RECEIVE:
                in_chn = event.peer.incomingPeerID
                epeer = event.peer
                msg = event.packet.data
                    #send (int channelID, Packet packet)
                rpckt = enet.Packet(msg)
                sendable = (epeer,in_chn,msg)
                outqueue.put(sendable)  #blocks until... outqueue is usable?
                if event.packet.data == b"SHUTDOWN":
                    shutdown_recv = True
                printstring = "%s: out: %r" % (event.peer.address, msg)
                responses.put(("printable",printstring))

        print("rare blocking write. connection closure called, time to clean up.")
    except KeyboardInterrupt:
        run = False
        print("terminating echo protocol")
    #sys.exit(130) #this might corrupt script structs :) i think that's cool :)

def enet_worker(inqueue, outqueue, responses):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")
    ethreadz = [threading.Thread(target=enet_inbound, args=(host, inqueue, outqueue, responses, )),
    threading.Thread(target=enet_outbound, args=(host, inqueue, outqueue, responses, ))]
    for t in ethreadz:
        t.start()

    for t in ethreadz:
        t.join()
    #technically this would let, uh, stuff close, i guess? yeah i dunno.

def host_worker(inqueue, outqueue, responses):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")
    hosthreadz = [threading.Thread(target=echo_protocol, args=(inqueue, outqueue, responses, )),
    threading.Thread(target=blocky_printer, args=(responses, ))]

    for ht in hosthreadz:
        ht.start()

    for ht in hosthreadz:
        ht.join()
    #yyee haww

def main():
    enet_peer_capacity = 4095 # please don't find a way to saturate this
    enet_channel_capacity = 128 #again please don't find a way to saturate 2^13 channels
    host = enet.Host(enet.Address("localhost", 33333), enet_peer_capacity, enet_channel_capacity, 0, 0)
    host.checksum = enet.ENET_CRC32
    """ #migrated these bad boys into the enet worker context!
    connect_count = 0
    run = True
    shutdown_recv = False
    """

    sorites = Queue()
    eubulides = Queue()
    responses = Queue()

    processez = [Process(target=enet_worker, args=(host, sorites, eubulides, responses, )), 
    Process(target=host_worker, args=(sorites, eubulides, responses, ))]

    for pz in processez:
        pz.start()

    #bunch of unbounded loops happen in here

    for pz in processez:
        pz.join()

    print("somehow we reached the end of control flow!")

    """
    while run:
        #check immediately for EnvironmentError
        event = host.service(0) # wait 250ms for network activity
        sorites.put(event)
        if event.type == enet.EVENT_TYPE_CONNECT:
            print("%s: connecto" % event.peer.address)
            connect_count +=1
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            print("%s: unconnecto" % event.peer.address)
            connect_count -=1
            if connect_count <= 0 and shutdown_recv:
                print("%s remaining sessions" % connect_count)
                run = False
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            print("%s: IN:  %r" % (event.peer.address, event.packet.data))
            msg = event.packet.data
            #really irritating line there.
            #peer.c contains a fn send().
            #that fn returns -1 if... some null check, i think for datalength == NULL.
            #stinky stinky stinky convention to call a function inside of a conditional!
            sendstatus = event.peer.send(0, enet.Packet(msg))
            if sendstatus == -1 :
                print("%s: uh oh in the echo packeto" % event.peer.address)
                continue
            print("%s: out: %r" % (event.peer.address, msg))
            if event.packet.data == b"SHUTDOWN":
                shutdown_recv = True
    """

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)