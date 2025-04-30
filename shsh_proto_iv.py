#shsh_proto_iv.py
import sys, os
import enet
import multiprocessing as mproc
import threading
#screm
import signal
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
    #ENET_IN_STOP = vile_semaphore[0:1]         
#       🗡re: semaphore aliases:
    #FULLSTOP = vile_semaphore[4]
    #ENET_IN_STOP = vile_semaphore[0] 
    #ENET_OUT_STOP= vile_semaphore[1]
    #BLOCKY_PRINTER_STOP = vile_semaphore[2]
    #ECHO_PROTOCOL_STOP = vile_semaphore[3]
    #THREADPOOL_STOP = vile_semaphore[5]
    #while run and not (FULLSTOP or *):
    #revised:
    #while run and not (vile_semaphore[4] or vile_semaphore[idx]):
#3: EXCEPTION HANDLING WOOOO EXCEPT TIME EXCEPT EXCEPT EXCEPT!!!!
#   3a: also we wrapped the loop terminator checks in a named function semaphore_NOR()
#       3aa: this makes the common semantics of the loop terminators less ambiguous
#   3b: i refuse to test this in more detail but i think you can use exceptions now
#       3ba: don't! don't try to use them! use IPC message pops (queues) or semaphores instead! 
#   3c: join() is now delayed by a THREADPOOL_STOP semaphore read.
#       3ca: join() is C-backend unsafe. 
#         it blocks exceptions literally forever without absorbing effects of exceptions. 
#         this means your programs produce garbage out-of-order effects from exceptions
#         but only *after* the program has exited the state that created the exception!
#         you get all of the problems of exceptions but none of the remedies they support. 
#4: maybe some feature code 👉👈🥺
#  



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
#syskill(...) -> checkflag(...) for normal shutdowns
#sysULTRAkill(...) -> checkflag(...) for ULTRA shutdowns
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
    #throw each individual syskill channel
    #0 for non-effect, 1 for effect.
def all_threadpool_syskill(vile_semaphore):
    vile_semaphore[5]=1

def all_bus_sys_ULTRAkill(vile_semaphore):
    for i in range(len(vile_semaphore)+1):
        vile_semaphore[i]=1
    #throw EVERY switch 
    #0 for non-effect, 1 for effect.

#signal block:
# this *is* a signal handler.
def signal_handler(signum, frame):
    #this is a debug string but i love it and you'll have to pay me to change it
    print(f"Received {signum}! raising poopdick!")
    raise KeyboardInterrupt

#this one should add signal callers to a function's context.
#so wrap every mfer with this thing.
#remember that interrupt events are like. wishy washy.
#they can *happen*, basically hook to programs as 'happening soon'.
#then trigger at unexpected times, or after they're logically invalid, etc.
#there are probably some metaprogramming tools we have not derived which let us track them.
#for now, be ready for exceptions to *fundamentally break* any code in any context without
#encircling try: except: finally:. good luck out there.
def exctransducer(sigsigdotsigdotsigtype,  fn, *args, **kwargs):
    #pass list of tuples of signal.signal(signal.SIGINT, signal_handler) args
    for sigdotsigtype in sigsigdotsigdotsigtype:
        signal.signal(sigdotsigtype[0], sigdotsigtype[1])
    #how many signals should we handle? all of them!
    try:
        fn(*args,**kwargs)
    #shsh_proto_iv.py:
    #this 'vibes like term request' exception catcher never seems to trigger.
    #instead, our signal handler raises, 3 CHECKFLAG signals fire,
    #print worker terminates, protocol services terminate, and network I/O gracefully terminates.
    #i *cannot truly say* whether this is good or bad.
    #what matters most is whether we can hide this nonsense from the elements of our programs which do real work.
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt)):
            print(f"that exception vibed like term request!!!")
            #u'd put termination logic here if you got any
            pass
        #pass if ur evil raise if ur good
        #if i read my own slop right
        raise

#stick this inside of a lexical scope which will try: except: finally:.
#specifically, in the try: 
#part, if you intend to pass keyboardinterrupts + trigger shutdowns.
#basically ```while run and semaphore_NOR(args):```
#wait a flop flipping minute this is A UNIVERSAL GATE AIAEIEIEIEIEEEEE
def semaphore_NOR(indices_NUTTES, loathesome_semaphore):
    carry = False   #good thing registers are free :)
    for indic in indices_NUTTES:
        carry = carry or loathesome_semaphore[indic]
        if carry:
            return not carry    #EARLY EXIT WOOOO OOOOOO OOOOOOOOOOO!!!!!!
    return not carry

#ENET BLOCK:
def enet_inbound(evil_ass_kvstore, ipc_queues, vile_semaphore):   

    #🗡re: semaphore[idx]:
    #FULLSTOP = vile_semaphore[4]
    #ENET_IN_STOP = vile_semaphore[0:1] 

    #IPC process termination
    stopsema = [4,0]
    try:
        #setup loop conditions
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

        #loop
        while run and semaphore_NOR(stopsema, vile_semaphore): 
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
    except KeyboardInterrupt:
        vile_semaphore[0]=1    #its our flag :)
        pass
    finally:
        pass
        #who knows what goes here lol

def enet_outbound(evil_ass_kvstore, ipc_queues, vile_semaphore):
        #FULLSTOP = vile_semaphore[4]
    #ENET_OUT_STOP= vile_semaphore[1]

    stopsema=[4,1]
    try:
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

        while run and semaphore_NOR(stopsema, vile_semaphore):       
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
    except KeyboardInterrupt:
        vile_semaphore[1]=1    #its our flag :)
        pass
    finally:
        pass
        #yeah idk what goes here

#PROTOCOL BLOCK
def blocky_printer(ipc_queues, vile_semaphore):
    #FULLSTOP = vile_semaphore[4]
    #BLOCKY_PRINTER_STOP = vile_semaphore[2]

    stopsema = [4,2]
    try:
        run=True

        #inqueue = ipc_queues["sorites"]["bus"]
        #outqueue = ipc_queues["eubulides"]["bus"]
        responses = ipc_queues["responses"]["bus"]


        while run and semaphore_NOR(stopsema, vile_semaphore):
            printable = responses.get()
            if printable[0] == 'CHECKFLAG':
                #wake up blocked function
                continue
            print(printable[1])
    except KeyboardInterrupt:
        print("we are shuttin this OFF")
        all_bus_sys_ULTRAkill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        all_threadpool_syskill(vile_semaphore)
        pass    #teehee
    finally:
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        print("ＢＥＷＡＲＥ！ PRINT WORKER TERMINATED")


def echo_protocol(ipc_queues, vile_semaphore):    
    #FULLSTOP = vile_semaphore[4]
    #ECHO_PROTOCOL_STOP = vile_semaphore[3]
    #while run and not (FULLSTOP or ECHO_PROTOCOL_STOP):
    stopsema = [4,3]
    try:
        connect_count = 0
        run = True
        shutdown_recv = False

        inqueue = ipc_queues["sorites"]["bus"]
        outqueue = ipc_queues["eubulides"]["bus"]
        responses = ipc_queues["responses"]["bus"]

        while run and semaphore_NOR(stopsema, vile_semaphore):

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
        #this fires if the while block closes all on its own!
        #print("mprcs:echo_protocol:rare blocking write. network-called closure conditionalized. time to clean up.")
    except KeyboardInterrupt:
        all_bus_sys_ULTRAkill(vile_semaphore)
        print("mprc:echo_protocol:deliver FORBIDDEN IPC MORDHAU!\nall_bus_sys_ULTRAkill called!")
        all_bus_checkflag(ipc_queues,vile_semaphore)
        all_threadpool_syskill(vile_semaphore)
        pass
    finally:
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        all_threadpool_syskill(vile_semaphore)
        #pass
        #yeah i dunno what you'd do here. 

#THREADING BLOCK
def enet_worker(host_args, ipc_queues, vile_semaphore):
 
    stopsema = [4,5]
    try:
        #print(f"Arguments: {args}")
        evil_ass_kvstore = {"host_args":host_args}

        #ssdsdst= ((signal.SIGINT, signal_handler),)
        #ex.:
        #target=exctransducer, args=(ssdsdst, enet_worker, host_args, ipc_queues, vile_semaphore, 
        #but what if. what if THREADS are also evil in the same way PROCESSES are evil? lets add even MORE signal handlers
        """ #don't ask me why this implementation isn't the right one.
        ethreadz = [
        threading.Thread(target=exctransducer, args=(ssdsdst, enet_inbound, evil_ass_kvstore, ipc_queues, vile_semaphore,)),
        threading.Thread(target=exctransducer, args=(ssdsdst, enet_outbound, evil_ass_kvstore, ipc_queues, vile_semaphore,))
        ]
        """
        ethreadz = [
        threading.Thread(target=enet_inbound, args=(evil_ass_kvstore, ipc_queues, vile_semaphore,)),
        threading.Thread(target=enet_outbound, args=(evil_ass_kvstore, ipc_queues, vile_semaphore,))]

        for t in ethreadz:
            t.start()

        while semaphore_NOR(stopsema,vile_semaphore):
            pass
        #maybe it's the join call that's problematic?
        #for t in ethreadz:
        #    t.join()
    except KeyboardInterrupt:
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        pass
    finally:
        for t in ethreadz:
            t.join()
        print("ＢＥＷＡＲＥ！ NETWORK I/O TERMINATED")
        #all_bus_checkflag(ipc_queues,vile_semaphore)
        #print("threw out an all_bus_checkflag from host_worker")

def host_worker(ipc_queues, vile_semaphore):

    stopsema = [4,5]
    try:
        #ssdsdst= ((signal.SIGINT, signal_handler),)
        #ex.:
        #target=exctransducer, args=(ssdsdst, enet_worker, host_args, ipc_queues, vile_semaphore, 
        #but what if. what if THREADS are also evil in the same way PROCESSES are evil? lets add even MORE signal handlers
        """
        hosthreadz = [
        threading.Thread(target=exctransducer, args=(ssdsdst, echo_protocol, ipc_queues, vile_semaphore, )),
        threading.Thread(target=exctransducer, args=(ssdsdst, blocky_printer, ipc_queues, vile_semaphore, ))
        ]
        """
        hosthreadz = [threading.Thread(target=echo_protocol, args=(ipc_queues, vile_semaphore, )),
        threading.Thread(target=blocky_printer, args=(ipc_queues, vile_semaphore, ))]

        for ht in hosthreadz:
            ht.start()

        while semaphore_NOR(stopsema,vile_semaphore):
            pass
        #maybe it's the join call that's problematic? dunno.
        #yes the join call is what's problematic. blocking on it stops IPC to thread handler.
        #for ht in hosthreadz:
        #    ht.join()
    except KeyboardInterrupt:
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        pass
    finally:
        for ht in hosthreadz:
            ht.join()
        print("ＢＥＷＡＲＥ！ PROTOCOL SERVICES TERMINATED")
        all_bus_checkflag(ipc_queues,vile_semaphore)
        print("threw out an all_bus_checkflag from host_worker")
    
    #print("threw out a FULLSTOP & all_bus_checkflag from host_worker")

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

    #🗡re: semaphore aliases:
    #revised:
    #while run and not (vile_semaphore[4] or vile_semaphore[idx]):
    vile_semaphore = mproc.Array('i', 6, lock=False)
    sorites = mproc.Queue() 
    eubulides = mproc.Queue()
    responses = mproc.Queue()

    #🗡def exccatcher(...)
    signal.signal(signal.SIGINT, signal_handler)
    ssdsdst= ((signal.SIGINT, signal_handler),)

    if __name__ == '__main__':
        print(f"created vile_semaphore from main:{vile_semaphore}")

    ipc_queues = {
        'sorites'   :{'bus':sorites,  'CHECKFLAG':("CHECKFLAG", None, None, None)},
        'eubulides' :{'bus':eubulides,'CHECKFLAG':("CHECKFLAG", None)},
        'responses' :{'bus':responses,'CHECKFLAG':("CHECKFLAG","Unexpected CHECKFLAG print?")}
    }

    """
    processez = [
        mproc.Process(target=enet_worker, args=(host_args, ipc_queues, vile_semaphore, )), 
    mproc.Process(target=host_worker, args=(ipc_queues, vile_semaphore, ))
    ]
    """
    
    processez = [   #we rotate the arguments to the right as the exechamp enters context to make enough room
    mproc.Process(target=exctransducer, args=(ssdsdst, enet_worker, host_args, ipc_queues, vile_semaphore, )), 
    mproc.Process(target=exctransducer, args=(ssdsdst, host_worker, ipc_queues, vile_semaphore, ))
    ]
    

    try:
        for pz in processez:
            pz.start()

        if __name__ == '__main__':
            print("despite starting processes, *somebody* is still the main thread. and it's main().")
        #bunch of unbounded loops happen in here

        #for some reason process join is exception safe but thread join isn't.
        for pz in processez:
            pz.join()
    except KeyboardInterrupt:
        print('Explicit interruption reached __main__ context! how curt')
        all_bus_syskill(vile_semaphore)
        all_bus_checkflag(ipc_queues,vile_semaphore)
        print('attempted clean shutdown, now attempting process join()')
        for pz in processez:
            pz.join()
        pass
    #finally:
    #    pass
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