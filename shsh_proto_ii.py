#shsh_proto_i.py
import sys, os
import enet
import multiprocessing as mproc
import threading
#packets
import msgspec

#pitfalls we are eluding:
#1: non-protocol debug returns, e.g. a pure echo server.
#   1a: why can't we return a PROTOCOLERROR: "YOU SEEM TO HAVE FORGOTTEN YOUR HEADERS?"
#   1b: a PROTOCOLERROR can have a body which has the echo data anyways!
#2: implict rather than explicit IPC protocols
#   2a: network packets aren't different enough from same-script IPC queue events
#   2b: we have been serializing those mfers anyways!
#       2ba: why didn't i notice that faster?
#3:event connection table:
#       🗡re: enet.pyx: 
    #   This class should never be instantiated directly, but rather via
    #   enet.Host.connect or enet.Event.Peer.
    #this means that... our connection table should have dereferenced
    #a `.peer` from our events this entire time,
    #rather than creating a connection table row for each network event
    #and then dereferencing the events to peers inside of ...outbound()

#actions:
#1: pass buses by reference to complex data type (dict)
#   1a: want a bus? dereference the a dict w/ bus's pointer (& checkflag magic header)
#     1aa: then dereference the bus's pointer from that dict.
#     1aa: yes i appreciate that sounds really nasty but welcome 2 abstraction
#2: concurrency interrupt and closure:
#       🗡re: semaphore[idx]:
    #okay it turns out you CANNOT get views from lists in python as objects.
    #the closest approximation is a function returning idx from list.
    #this function def works:
    #def FULLSTOP():
    #    return vile_semaphore[4]
    #this alias attempt does not work! not even as a slice!
    #ENET_IN_STOP = vile_semaphore[0:1]         
#       🗡re: semaphore aliases:
    #FULLSTOP = vile_semaphore[4]
    #ENET_IN_STOP = vile_semaphore[0] 
    #ENET_OUT_STOP= vile_semaphore[1]
    #BLOCKY_PRINTER_STOP = vile_semaphore[2]
    #ECHO_PROTOCOL_STOP = vile_semaphore[3]
    #while run and not (FULLSTOP or *):
    #revised:
    #while run and not (vile_semaphore[4] or vile_semaphore[idx]):

#evil helper functions block
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

#semaphore helper functions block
def all_bus_checkflag(ipc_queues, vile_semaphore):
    #b_b_queues=ipc_queues #dont ask
    bus_buster = len(threading.enumerate())
    print("caught u threading O(%sx%s)" % (bus_buster, len(ipc_queues.keys())))
    for que in ipc_queues.keys():
        for thrd in range(bus_buster):
            ipc_queues[que]["bus"].put(ipc_queues[que]["CHECKFLAG"])

def all_bus_syskill(vile_semaphore):
    for i in range(4):
        vile_semaphore[i]=1
    #0 for non-effect, 1 for effect.

#ENET BLOCK:
def enet_inbound(evil_ass_kvstore, ipc_queues, vile_semaphore):   
    #import enet
    host_args = evil_ass_kvstore["host_args"]
    eadd = enet.Address(*host_args[0])  #unpack uhh hostname uhh port
    enethost = enet.Host(eadd, *host_args[1])
    enethost.checksum = enet.ENET_CRC32

    #be careful with this one, 
    # rmbr that you have to confirm this has actually been written 
    # before u announce its availability to other services which might need it.
    #evil_ass_kvstore["host"] = enethost

    inqueue = ipc_queues["sorites"]["bus"]
    outqueue = ipc_queues["eubulides"]["bus"]
    responses = ipc_queues["responses"]["bus"]

    ticker = 0
    run=True

    #🗡re: semaphore[idx]:
    #okay it turns out you CANNOT get views from lists in python as objects.
    #the closest approximation is a function returning idx from list.
    #def FULLSTOP():
    #    return vile_semaphore[4]
    #ENET_IN_STOP = vile_semaphore[0:1] 

    while run and not vile_semaphore[4] and not vile_semaphore[0]:
        #pre-polling block
        #if vile_semaphore[0]:
        #    run = False

        # wait {operand} ms for network activity
        event = enethost.service(0) 
        
        #post-polling block;
        #thread now has 'hot' state that it *must* handle, 
        # even by explicitly reporting non-handling.
        #non-event must prefix event handling
        if int(event.type) == int(enet.EVENT_TYPE_NONE):
            #why check semaphores on every cycle whether or not an event happened?
            continue
        
        #event handling block
        #implicitly qualified by not-non-event
        ticker +=1

        #!REFACTOR WARNING!
        #older implementation logged events. 
        #this is most coherent for data streams but what if we're deferring results?
        #we ultimately need a connection table...
        #which joins task UUIDs to peers who assert claims to task UUIDs.
        ykey = repr(ticker)
        evil_ass_kvstore[ykey] = event

        #!REFACTOR WARNING!
        #THIS IS A PACKET FORMATION SCENARIO. SUS UP!!!
        if int(event.type) == int(enet.EVENT_TYPE_CONNECT):
            yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_DISCONNECT):
            yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_RECEIVE):
            yeetable_event = (ykey, int(event.type), str(event.peer.address), event.packet.data)

        #!REFACTOR WARNING!
        #IPC transmission scenario. stay noided.
        inqueue.put(yeetable_event) #blocking ipc i guess!!!
    #if FULLSTOP:
    #    sys.exit()
    #if ENET_IN_STOP:
    #    enethost.flush()
    #    sys.exit()


def enet_outbound(evil_ass_kvstore, ipc_queues, vile_semaphore):
    #enethost = evil_ass_kvstore["host"]
    run=True
    
    inqueue = ipc_queues["sorites"]["bus"]
    outqueue = ipc_queues["eubulides"]["bus"]
    responses = ipc_queues["responses"]["bus"]

    #enet helper functions block
    def compose_bflags(list):
        carrier = int(0)
        for fl in list:
            carrier|fl
        return carrier

    pflags = compose_bflags(
        [enet.PACKET_FLAG_UNSEQUENCED,
        enet.PACKET_FLAG_UNRELIABLE_FRAGMENT]
        )

    FULLSTOP = vile_semaphore[4]
    ENET_OUT_STOP= vile_semaphore[1]

    while run: # and not (FULLSTOP or ENET_OUT_STOP):
        #pre-polling block
        if vile_semaphore[1]:
            #check semaphores before slow blocking call
            run = False
            continue
        
        #unlimited block awaiting network outputs
        #
        sendable = outqueue.get()
        # (y_event[0],rpckt)   
        # evil_ass_kvstore identifier, protocol return packet
        
        #post-polling block;
        if sendable[0] == 'CHECKFLAG':
            #wake up blocked function
            continue
        #!REFACTOR WARNING!
        #this is the ONLY mechanism limiting infinite event table bloat??
        if sendable[1] is None:
            responses.put(("printable","purged None-returned entry from connection table."))
            del evil_ass_kvstore[sendable[0]]
            continue

        event = evil_ass_kvstore[sendable[0]]
        payload = enet.Packet(sendable[1], pflags)
        #compose unsequenced unreliable packet!
        
        #uses event.peer.send()?? not enet.peer.send()???
        #   🗡re: enet.pyx: ...
        sendstatus = event.peer.send(event.peer.incomingPeerID, payload)
        if sendstatus == -1 :
            printstring = "%s: uh oh in the echo packeto — intended payload was %s" % (str(event.peer.address), sendable[1][:80])
            responses.put(("printable",printstring))
            del evil_ass_kvstore[sendable[0]]
            continue
        #printstring = "mprcs:enet_outbound:%s: chn:%s out: %r" % (str(event.peer.address), str(event.peer.incomingPeerID), sendable[1][:80])
        #responses.put(("printable",printstring))
        del evil_ass_kvstore[sendable[0]]
    #cleanup:
    #if FULLSTOP:
        #enethost = evil_ass_kvstore["host"]
        #enethost.flush()
        #sys.exit()
    #how do we get the host reference to enet_outbound?
    #if ENET_OUT_STOP:
    #    enethost.flush()
    #    sys.exit()


#PROTOCOL BLOCK

def blocky_printer(ipc_queues, vile_semaphore):
    run=True

    #inqueue = ipc_queues["sorites"]["bus"]
    #outqueue = ipc_queues["eubulides"]["bus"]
    responses = ipc_queues["responses"]["bus"]

    FULLSTOP = vile_semaphore[4]
    BLOCKY_PRINTER_STOP = vile_semaphore[2]

    while run and not (FULLSTOP or BLOCKY_PRINTER_STOP):
        if vile_semaphore[2]:
            #check semaphores before slow blocking call
            run = False
            print("ＢＥＷＡＲＥ！ PRINT WORKER TERMINATED")
            continue

        printable = responses.get()

        if printable[0] == 'CHECKFLAG':
            #wake up blocked function
            continue
        print(printable[1])



def echo_protocol(ipc_queues, vile_semaphore):    
    connect_count = 0
    run = True
    shutdown_recv = False

    inqueue = ipc_queues["sorites"]["bus"]
    outqueue = ipc_queues["eubulides"]["bus"]
    responses = ipc_queues["responses"]["bus"]

    FULLSTOP = vile_semaphore[4]
    ECHO_PROTOCOL_STOP = vile_semaphore[3]
    #while run and not (FULLSTOP or ECHO_PROTOCOL_STOP):

    while run and not (FULLSTOP or ECHO_PROTOCOL_STOP):
        if vile_semaphore[3]:
            #check semaphores before slow blocking call
            run = False
            continue

        if connect_count <= 0 and shutdown_recv:
            printstring = "%s remaining sessions" % connect_count
            responses.put(("printable",printstring))
            run = False
            #responses.put(("printable","echo_protocol run status: %s" % run))
            continue

        y_event = inqueue.get() #blocks until something is queued. 
        #y_event (ykey, event.type, event.peer.address, event.packet.data.decode())

        if y_event[0] == 'CHECKFLAG':
            continue

        if y_event[1] == int(enet.EVENT_TYPE_CONNECT):
            printstring ="%s: connecto" % y_event[2] # peer address
            responses.put(("printable",printstring))
            connect_count +=1
            #purge evil_ass_kvstore event before y_event[0] reference expires
            nonsendable = (y_event[0],None)
            outqueue.put(nonsendable)

        elif y_event[1] == int(enet.EVENT_TYPE_DISCONNECT):
            printstring ="%s: unconnecto" % y_event[2] # peer address
            responses.put(("printable",printstring))
            connect_count -=1
            #purge evil_ass_kvstore event before y_event[0] reference expires
            nonsendable = (y_event[0],None)
            outqueue.put(nonsendable)

        elif y_event[1] == int(enet.EVENT_TYPE_RECEIVE):
            #send (int channelID, Packet packet)
            rpckt = y_event[3]
            sendable = (y_event[0],rpckt)   #we can't presume a decoding bc non-utf8 bytes are possible
            #peer id key, echo packet. remember this is still only an echo server!
            #also remember to reencode that message to bytes. haha.
            outqueue.put(sendable)  #blocks until... outqueue is usable?
            if rpckt == b"SHUTDOWN":
                shutdown_recv = True
                responses.put(("printable","shutdown flag status: %s" % shutdown_recv))
            printstring = "%s: out: %r" % (y_event[2], y_event[3][0:80])
            responses.put(("printable",printstring))   #print safeguard

    print("mprcs:echo_protocol:rare blocking write. connection closure called, time to clean up.")
    all_bus_syskill(vile_semaphore)
    all_bus_checkflag(ipc_queues,vile_semaphore)
    #FULLSTOP=1

#THREADING BLOCK

def enet_worker(host_args, ipc_queues, vile_semaphore):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")
    evil_ass_kvstore = {"host_args":host_args}
    ethreadz = [threading.Thread(target=enet_inbound, args=(evil_ass_kvstore, ipc_queues, vile_semaphore,)),
    threading.Thread(target=enet_outbound, args=(evil_ass_kvstore, ipc_queues, vile_semaphore,))]
    
    for t in ethreadz:
        t.start()

    for t in ethreadz:
        t.join()

    print("ＢＥＷＡＲＥ！ NETWORK I/O TERMINATED")
    #technically this would let, uh, stuff close, i guess? yeah i dunno.

def host_worker(ipc_queues, vile_semaphore):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")

    FULLSTOP = vile_semaphore[4]

    hosthreadz = [threading.Thread(target=echo_protocol, args=(ipc_queues, vile_semaphore, )),
    threading.Thread(target=blocky_printer, args=(ipc_queues, vile_semaphore, ))]


    for ht in hosthreadz:
        ht.start()

    for ht in hosthreadz:
        ht.join()

    print("ＢＥＷＡＲＥ！ PROTOCOL SERVICES TERMINATED")
    all_bus_checkflag(ipc_queues,vile_semaphore)
    print("threw out an all_bus_checkflag from host_worker")
    FULLSTOP=1
    all_bus_checkflag(ipc_queues,vile_semaphore)
    print("threw out a FULLSTOP & all_bus_checkflag from host_worker")

    #yyee haww

def main():
    enet_peer_capacity = 4095 # please don't find a way to saturate this
    enet_channel_capacity = 128 #again please don't find a way to saturate 2^13 channels
    #host = enet.Host(enet.Address("localhost", 33333), enet_peer_capacity, enet_channel_capacity, 0, 0)
    #host.checksum = enet.ENET_CRC32
    #
    # forking pickler got us! it was always illegal to pass a cython object across threads
    # *even as an operand*! 
    host_args = (("localhost",33333), (enet_peer_capacity, enet_channel_capacity, 0, 0))
    """ #migrated these bad boys into the enet worker context!
    connect_count = 0
    run = True
    shutdown_recv = False
    """

    #🗡re: semaphore aliases:
    #revised:
    #while run and not (vile_semaphore[4] or vile_semaphore[idx]):
    vile_semaphore = mproc.Array('i', 5, lock=False)
    sorites = mproc.Queue() 
    eubulides = mproc.Queue()
    responses = mproc.Queue()
    if __name__ == '__main__':
        print(f"created vile_semaphore from main:{vile_semaphore}")

    ipc_queues = {
        'sorites'   :{'bus':sorites,  'CHECKFLAG':("CHECKFLAG", None, None, None)},
        'eubulides' :{'bus':eubulides,'CHECKFLAG':("CHECKFLAG", None)},
        'responses' :{'bus':responses,'CHECKFLAG':("CHECKFLAG","Unexpected CHECKFLAG print?")}
    }

    processez = [mproc.Process(target=enet_worker, args=(host_args, ipc_queues, vile_semaphore, )), 
    mproc.Process(target=host_worker, args=(ipc_queues, vile_semaphore, ))]

    try:
        for pz in processez:
            pz.start()

        if __name__ == '__main__':
            print("despite starting processes, *somebody* is still the main thread. and it's main().")
        #bunch of unbounded loops happen in here

        for pz in processez:
            pz.join()
    except KeyboardInterrupt:
        print('Explicitly interrupted from __main__ context! how curt')
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        print('attempted clean shutdown, now attempting process join()')
        for pz in processez:
            pz.join()


    #print("somehow we reached the end of control flow!")
    #print(f"this multiprocessing.active_children() better b zero: {mproc.active_children()}")

if __name__ == '__main__':
    """
    try:
    """
    main()
    """
    except KeyboardInterrupt:
        print('Explicitly interrupted from global state! how daring')
        all_bus_syskill(evil_outer_semaphore)
        all_bus_checkflag(ipc_queues,evil_outer_semaphore)
        sys.exit(130)
    """