#mproc_pyenet_serv
import sys, os
import enet
import multiprocessing as mproc
import threading

#update threading is cursed
#maybe asyncio hard to say.

def enet_inbound(evil_kvstore, inqueue, outqueue, responses):   #refactored to event-non-passing
    import enet
    host_args = evil_kvstore["host_args"]
    eadd = enet.Address(*host_args[0])  #unpack uhh hostname uhh port
    enethost = enet.Host(eadd, *host_args[1])
    print(eadd)
    responses.put(("printable",str(eadd)))
    responses.put(("printable",str(eadd)))
    responses.put(("printable",repr(evil_kvstore)))
    ticker = 0
    run=True
    while run:
        event = enethost.service(100) # wait {operand} ms for network activity
        #responses.put(("printable",int(event.type)))

        if int(event.type) == int(enet.EVENT_TYPE_NONE):
            continue #it would be *really* weird to saturate queue with non-events!
            
        print(event)
        ticker +=1
        ykey = repr(ticker)
        evil_kvstore[ykey] = event
        print(ticker+", "+ykey)
        #a repr is a unique id if you're brave enough
        #as... a str(magnitude) operation has log(n) complexity, 
        #the use of an unbounded counter will cause log(n) latency with n successfully managed connections

        if int(event.type) == int(enet.EVENT_TYPE_CONNECT):
            # i don't have a good way to read the C side of the lib?
            # it looks like a pointer based copy of eventData
            # is triggered for populating the event.data field 
            # for the connect event, however the contents are ambiguous.
            yeetable_event = (ykey, int(event.type), repr(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_DISCONNECT):
            # so above so down here
            yeetable_event = (ykey, int(event.type), repr(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_RECEIVE):
            yeetable_event = (ykey, event.type, event.peer.address, event.packet.data.decode())

        inqueue.put(yeetable_event) #blocking ipc i guess!!!


def enet_outbound(evil_kvstore, inqueue, outqueue, responses):  #refactored.
    #enethost = evil_kvstore["host"]
    run=True
    try:
        while run:
            sendable = outqueue.get()
            # (y_event[0],rpckt)   
            # evil_kvstore identifier, multiprocessing concurrency calculated return packet
            event = evil_kvstore[sendable[0]]

            #sends and gets a return object. return only meaningful in case of errors.
            sendstatus = event.peer.send(event.peer.incomingPeerID, sendable[1])
            if sendstatus == -1 :
                printstring = "%s: uh oh in the echo packeto" % str(event.peer.address)
                responses.put(("printable",printstring))
                del evil_kvstore[sendable[0]]
                continue
            printstring = "%s: chn:%s out: %r" % (str(event.peer.address), str(event.peer.incomingPeerID), sendable[1])
            responses.put(("printable",printstring))
            del evil_kvstore[sendable[0]]
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

def echo_protocol(inqueue, outqueue, responses):    #refactored to event-non-passing
    connect_count = 0
    run = True
    shutdown_recv = False
    try:
        while run:
            y_event = inqueue.get() #blocks until something is queued. 
            #y_event (ykey, event.type, event.packet.data.decode())

            if y_event[1] == int(enet.EVENT_TYPE_CONNECT):
                printstring ="%s: connecto" % y_event[2] # peer address
                responses.put(("printable",printstring))
                connect_count +=1

            elif y_event[1] == int(enet.EVENT_TYPE_DISCONNECT):
                printstring ="%s: unconnecto" % y_event[2] # peer address
                responses.put(("printable",printstring))
                connect_count -=1

                if connect_count <= 0 and shutdown_recv:
                    printstring = "%s remaining sessions" % connect_count
                    responses.put(("printable",printstring))
                    run = False

            elif y_event[1] == int(enet.EVENT_TYPE_RECEIVE):
                #send (int channelID, Packet packet)
                rpckt = y_event[2]
                sendable = (y_event[0],rpckt)   #peer id key, echo packet. remember this is still only an echo server!
                outqueue.put(sendable)  #blocks until... outqueue is usable?
                if rpckt == b"SHUTDOWN":
                    shutdown_recv = True
                printstring = "%s: out: %r" % (y_event[2], rpckt)
                responses.put(("printable",printstring))

        print("rare blocking write. connection closure called, time to clean up.")
    except KeyboardInterrupt:
        run = False
        print("terminating echo protocol")
    #sys.exit(130) #this might corrupt script structs :) i think that's cool :)

def enet_worker(host_args, inqueue, outqueue, responses):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")
    evil_kvstore = {"host_args":host_args}
    ethreadz = [threading.Thread(target=enet_inbound, args=(evil_kvstore, inqueue, outqueue, responses, )),
    threading.Thread(target=enet_outbound, args=(evil_kvstore, inqueue, outqueue, responses, ))]
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
    #host = enet.Host(enet.Address("localhost", 33333), enet_peer_capacity, enet_channel_capacity, 0, 0)
    #host.checksum = enet.ENET_CRC32
    #
    # forking pickler got us! it was always illegal to pass a cython *even as an operand*! 
    host_args = (("localhost",33333), (enet_peer_capacity, enet_channel_capacity, 0, 0))
    """ #migrated these bad boys into the enet worker context!
    connect_count = 0
    run = True
    shutdown_recv = False
    """

    sorites = mproc.Queue()
    eubulides = mproc.Queue()
    responses = mproc.Queue()

    processez = [mproc.Process(target=enet_worker, args=(host_args, sorites, eubulides, responses, )), 
    mproc.Process(target=host_worker, args=(sorites, eubulides, responses, ))]

    for pz in processez:
        pz.start()

    #bunch of unbounded loops happen in here

    for pz in processez:
        pz.join()

    print("somehow we reached the end of control flow!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)