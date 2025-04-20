#mproc_pyenet_serv_ii
import sys, os
import enet
import multiprocessing as mproc
import threading

#update threading is cursed

#update semaphorse are cursed
# candidate solution for making semaphores compatible with input-blocked threads:
# new message type for *all* queues which can input block any thread:
# CHECKFLAG
# all input blocked functions over queues must:
# implement 'buffer = some_queue.get();
# -> if buffer == queuetype_CHECKFLAG: 
# -> continue.
# *further*, all blocking functions need to check 
# shared memory in their loops before blocking for admin events.
# i feel like im being forced to derive a CPU interrupt implementation here.
# anyways whatever process receives administrative overrides needs to call
# bus_buster = len(threading.enumerate())
# for thrd in bus_buster:
#   for que in b_b_queues:
#       que["bus"].put(que["CHECKFLAG"])
# b_b_queues must define {'bus':<queue reference>,'CHECKFLAG':queuetype_CHECKFLAG}
# for all blocking queues used in program: what this means pragmatically is like
# {'responses':{'bus':responses,'CHECKFLAG':("CHECKFLAG","Unexpected CHECKFLAG print?")}}
def enet_inbound(evil_ass_kvstore, inqueue, outqueue, responses):   #refactored to event-non-passing
    #import enet
    host_args = evil_ass_kvstore["host_args"]
    eadd = enet.Address(*host_args[0])  #unpack uhh hostname uhh port
    enethost = enet.Host(eadd, *host_args[1])
    enethost.checksum = enet.ENET_CRC32

    # these lines were used to debug the type of cython objects while debugging IPCIO.
    # commit em, push em, delete em, diff em. git for all time how much we had to log.
    #print(eadd)
    #responses.put(("printable",str(eadd)))
    # server thread startup config print
    responses.put(("printable",repr(evil_ass_kvstore)))
    
    ticker = 0
    run=True
    while run:
        event = enethost.service(0) # wait {operand} ms for network activity
        # nonblocking or 0 ms service() call loops immediately. 
        # this means we must schedule server shutdown, 
        # flag enet_inbound.run = false,
        # process the *last* event we absorbed, then kill all other threads...
        # within *this* function.
        # doesn't this distributed control problem sorta. suck?

        if int(event.type) == int(enet.EVENT_TYPE_NONE):
            continue #it would be *really* weird to saturate queue with non-events!
        
        ticker +=1
        ykey = repr(ticker)
        evil_ass_kvstore[ykey] = event
        #a repr is a unique id if you're brave enough
        #as... a str(magnitude) operation has log(n) complexity, 
        #the use of an unbounded counter will cause log(n) latency with n successfully managed connections

        # these lines chronologue blocking vs nonblocking prints
        # don't uncomment these without *actually recording* the log level verbosity
        # don't delete them either (duh): they belong in at least one logging level.
        # it must be explicit that putting print calls inside of a process stalls that process.
        #print("mprc:enet_inbound():"+str(ticker)+", "+str(ykey))   
        #responses.put(("printable","mprc:blocky_printer:"+str(ticker)+", "+str(ykey)))

        if int(event.type) == int(enet.EVENT_TYPE_CONNECT):
            # i don't have a good way to read the C side of the lib?
            # it looks like a pointer based copy of eventData
            # is triggered for populating the event.data field 
            # for the connect event, however the contents are ambiguous.
            yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_DISCONNECT):
            # so above so down here
            yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
        elif int(event.type) == int(enet.EVENT_TYPE_RECEIVE):
            yeetable_event = (ykey, int(event.type), str(event.peer.address), event.packet.data.decode())

        inqueue.put(yeetable_event) #blocking ipc i guess!!!


def enet_outbound(evil_ass_kvstore, inqueue, outqueue, responses):  #refactored.
    #enethost = evil_ass_kvstore["host"]
    run=True
    try:
        while run:
            sendable = outqueue.get()
            # (y_event[0],rpckt)   
            # evil_ass_kvstore identifier, multiprocessing concurrency calculated return packet
            if sendable[1] is None:
                responses.put(("printable","purged None-returned entry from connection table."))
                del evil_ass_kvstore[sendable[0]]
                continue
                        
            event = evil_ass_kvstore[sendable[0]]
            payload = enet.Packet(sendable[1])
            #sends and gets a return object. return only meaningful in case of errors.
            sendstatus = event.peer.send(event.peer.incomingPeerID, payload)
            if sendstatus == -1 :
                printstring = "%s: uh oh in the echo packeto" % str(event.peer.address)
                responses.put(("printable",printstring))
                del evil_ass_kvstore[sendable[0]]
                continue
            printstring = "%s: chn:%s out: %r" % (str(event.peer.address), str(event.peer.incomingPeerID), sendable[1])
            responses.put(("printable",printstring))
            del evil_ass_kvstore[sendable[0]]
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
            if connect_count <= 0 and shutdown_recv:
                printstring = "%s remaining sessions" % connect_count
                responses.put(("printable",printstring))
                run = False
                responses.put(("printable","echo_protocol run status: %s" % run))
                #this conditional MUST have a `continue` or `break`` lest server block for inqueue!
                continue

            y_event = inqueue.get() #blocks until something is queued. 
            #y_event (ykey, event.type, event.peer.address, event.packet.data.decode())

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
                sendable = (y_event[0],rpckt.encode())   
                #peer id key, echo packet. remember this is still only an echo server!
                #also remember to reencode that message to bytes. haha.
                outqueue.put(sendable)  #blocks until... outqueue is usable?
                if rpckt == "SHUTDOWN":
                    shutdown_recv = True
                    responses.put(("printable","shutdown flag status: %s" % shutdown_recv))
                printstring = "%s: out: %r" % (y_event[2], rpckt)
                responses.put(("printable",printstring))

        print("mprcs:echo_protocol:rare blocking write. connection closure called, time to clean up.")
    except KeyboardInterrupt:
        run = False
        print("terminating echo protocol")
    #sys.exit(130) #this might corrupt script structs :) i think that's cool :)

def enet_worker(host_args, inqueue, outqueue, responses):
    #args = (inqueue, outqueue, responses)
    #print(f"Arguments: {args}")
    evil_ass_kvstore = {"host_args":host_args}
    ethreadz = [threading.Thread(target=enet_inbound, args=(evil_ass_kvstore, inqueue, outqueue, responses, )),
    threading.Thread(target=enet_outbound, args=(evil_ass_kvstore, inqueue, outqueue, responses, ))]
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
    # forking pickler got us! it was always illegal to pass a cython object across threads
    # *even as an operand*! 
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