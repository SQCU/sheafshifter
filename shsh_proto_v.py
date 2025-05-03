#shsh_proto_v.py
#PROTOCODER FUNCTION ADDITIONS PASS DRY RUN
import sys, os
import enet
import multiprocessing as mproc
import threading
#screm
import signal
#packets
import msgspec
import pickle #hehe
from functools import reduce

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
    #revised: 
    #stopsema = [4,*]
    #    while run and semaphore_NOR(stopsema, vile_semaphore):
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
#   3d: take caution: i wrote this while very tired. 
#     and maybe we should use: while ( try( ) )
#     right now our i/o loops appear to be: try ( while ( ) ).
#     if that sounds like a meaningless difference, it wasn't a mistake yet.
#       3da:reviewing source, try(while()) seems to target catching exceptions before core loops. 
#4: maybe some feature code 👉👈🥺
#5: FAT CHANCE! HEADERS AND DATA TYPES!!!
# 'CHECKFLAG':("CHECKFLAG", None, None, None)
# 'CHECKFLAG':("CHECKFLAG","Unexpected CHECKFLAG print?") 
# here are two improper and underspecified packets.
# there... sort of... is a header?
# that is to say, a program can check the 0th index for CHECKFLAG.
# if the program has CHECKFLAG in there, the packet has a certain type.
# all other packets... have a different type.
# anyways this suggests the backbone of the solution is *already* in the code!
# def protococoder()
# 1: No excuses. we have never read a wrong-typed input from INQUEUE.
#   we have never read a wrong-typed input from OUTQUEUE.
#   that doesn't *mean* anything.
#   this correctness was essentially coincidental.
#   'it never happened yet' isn't a reason to execute on garbage data, is it?
# 2: just pick a magic number already
# 3: stupid and bad formats are still formats, and a detectable format can be fixed later!



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

#internal interprocess communication protocol block
def pref(operandbytes=sbytes("NONE"), pickleable=sbytes("NONE")):
    #ipc protocol reference
    #pass IPC_field_code as bytes. yep get used to bytes buddy.
    #pass pickleable python object for consumption by complementary routine.
    #return packet ready 4 serialization, error stream.
    #bad inputs should probably be passed through instead of breaking control flow?
    #error return from ipcproto encode should be an empty list, (or a falsy 😌) when ur inputs arent bad
    #+4 bytes
    #constants:
    err=[]
    ver = int4bitter(967296)    #version 0=967,296. version+1=value+1.
    field2byte = {
        sbytes("SORITES")   :sbytes("a"),
        sbytes("EUBULIDES") :sbytes("b"),
        sbytes("WRITTEN")   :sbytes("c"),
        sbytes("NONE")      :sbytes("NNNnnn"),
    }
    default_pckl = b'\x80\x04\x95\x08\x00\x00\x00\x00\x00\x00\x00C\x04NONE\x94.'
    #non-constants:
    #+1 bytes
    if not operandbytes.decode("utf8").startswith(tuple(ke.decode("utf8") for ke in field2byte.keys())):   
        err.append(("IPCPROTO_ERROR",f"YOU PASSED SOMETHING WORSE THAN NOTHING AS AN IPC TARGET:{operandbytes}"))
        operandbytes = b"NONE"
    fieldbyte = field2byte[operandbytes]    #e.g. field2byte(b"SORITES")
    if (len(fieldbyte)-1):
        err.append(("IPCPROTO_ERROR","YOU DIDN'T PASS AN IPC BUS TARGET. THINK ABOUT WHAT THAT MEANS."))
    pckl = pickle.dumps(pickleable)
    if pckl==default_pckl:
        err.append(("PICKLE_WARNING","YOU PASSED A WEIRD STRUCT OR NO STRUCT AT ALL"))
    #try not to serialize anything bigger than 240gb okay???
    #+6 bytes
    codalen = int.to_bytes(len(pckl), 6,byteorder="big")
    #+1 byte should equal 12by
    headalen = intbitter(len(ver+fieldbyte+intbitter(1)+codalen))
    # 4+1+1+6
    heada = ver+fieldbyte+headalen+codalen
    return heada+pckl, err
def pdref(operandbytes):
    #ipc protocol dereference
    #pass serialized packet (meant for message-passing mproc queues)
    #expect (field, pystruct), [tuple(error_name,error_contents) for error_name, error_contents in your-broke-ah-ah-input]
    #that's right: the return is a dereferenced tuple of a tuple and a list of tuples.
    #error return should be an empty list, (or a falsy 😌) when ur inputs arent bad
    def bytewise_NOTORNOT(byties,bytiestwo):
        zzipp = list(zip(byties,bytiestwo))
        #print(zzipp)
        zippzer = [ ~(z[0]|~z[1]) for z in zzipp]
        #print(zippzer)
        return reduce(lambda x,y: x+y, zippzer)
        #this is a little bit performance art and a little bit late night coding
    err = []
    refver = int4bitter(967296) #version 0=967,296. version+1=value+1.
    #print(refver)
    ver=operandbytes[0:4]
    #print(ver)
    #verdiff = bytewise_NOTORNOT(refver,ver)
    #if verdiff:
    #    err.append(("VERSION_ERROR",verdiff))
    byte2field = {
        sbytes("a"):sbytes("SORITES"),
        sbytes("b"):sbytes("EUBULIDES"),
        sbytes("c"):sbytes("WRITTEN"),
        sbytes("NNNnnn"):sbytes("NONE"),
    }
    fieldbytes = operandbytes[4:5]
    #... can we get an error if we utf8 decode an arbitrary byte?
    #probably lol but who would ever write a wrong byte there?
    if not fieldbytes.decode("utf8").startswith(tuple(ke.decode("utf8") for ke in byte2field.keys())):   
        err.append(("IPCPROTO_ERROR",f"YOU DECODED SOMETHING SUSPICIOUSLY LIKE A NONE-FIELD:{repr(fieldbytes)}"))
        fieldbytes = b"NNNnnn"
    field = byte2field[fieldbytes]
    headalen = operandbytes[5:6] #teehee
    #codalen = operandbytes[6:headalen]
    coda = pickle.loads(operandbytes[intsweeten(headalen):])
    #return (field, coda), err   #lefty normal, righty errors
    #WOAH that was a weird choice of a return for a first patch. review later.
    return coda, err

#semaphore helper functions block
#syskill(...) -> checkflag(...) for normal shutdowns
#sysULTRAkill(...) -> checkflag(...) for ULTRA shutdowns
def all_bus_checkflag(ipc_queues, vile_semaphore):
    #b_b_queues=ipc_queues #dont ask

    cflg_to_ipcproto = {
        "sorites":"SORITES",
        "eubulides":"EUBULIDES",
        "responses":"WRITTEN",
    }

    def ret_meta_error(ipc_err):
        ipc_err_pckt, prt_err = pref(sbytes("WRITTEN"), ("printable",ipc_err))
        ipc_queues["responses"]["bus"].put(ipc_err_pckt)
        if prt_err:
            print("all_bus_checkflag:emergency meta-error failover print:%s:from:%s" % (prt_err,ipc_err))

    def serialize_IPC(fieldstring, pyobject):
        responses_ipc_packet, srlz_ipc_err = pref(sbytes(fieldstring), pyobject)
        if srlz_ipc_err:
            ret_meta_error(srlz_ipc_err)
        return responses_ipc_packet

    bus_buster = len(threading.enumerate())
    print("caught u threading O(%sx%s)" % (bus_buster, len(ipc_queues.keys())))
    ret_ipc_pckts = []
    for que in ipc_queues.keys():
        for thrd in range(bus_buster):
            #cflg_pyobj = ipc_queues[que]["CHECKFLAG"]
            cflg_pyobj = serialize_IPC(cflg_to_ipcproto[que],ipc_queues[que]["CHECKFLAG"])
            ipc_queues[que]["bus"].put(cflg_pyobj)

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

        def ret_meta_error(ipc_err):
            ipc_err_pckt, prt_err = pref(sbytes("WRITTEN"), ("printable",ipc_err))
            responses.put(ipc_err_pckt)
            if prt_err:
                print("mprcs:enet_inbound:emergency meta-error failover print:%s:from:%s" % (prt_err,ipc_err))

        def serialize_IPC(fieldstring, pyobject):
            responses_ipc_packet, srlz_ipc_err = pref(sbytes(fieldstring), pyobject)
            if srlz_ipc_err:
                ret_meta_error(srlz_ipc_err)
            return responses_ipc_packet

        def deserialize_IPC(ipc_packet):
            pyobject, desrlz_ipc_err = pdref(ipc_packet)
            if desrlz_ipc_err:
                ret_meta_error(desrlz_ipc_err)
            return pyobject

        ticker = 0
        run=True

        #loop
        stopsema = [4,0]
        while run and semaphore_NOR(stopsema, vile_semaphore): 
            # ! BIG shsh_proto_v.py UPDATE!
            # we wrote a packetizer which lets us remove all packetization logic from enet_inbound!
            # we still need the EVENT_TYPE_NONE handlign for now though. 

            # wait {operand} ms for network activity
            event = enethost.service(0) 
            
            #post-polling block;
            #thread now has 'hot' state that it *must* handle, 
            # even by explicitly reporting non-handling.
            #non-event must preempt event handling
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

            #refactor phase 1
            y_data = None
            if event.type == enet.EVENT_TYPE_RECEIVE:
                y_data = event.packet.data

            yeetable_event = (ykey, 
            int(event.type), 
            str(event.peer.address), 
            y_data)

            #refactor phase 1
            ipc_packet = serialize_IPC("SORITES", yeetable_event)
                
            #if int(event.type) == int(enet.EVENT_TYPE_CONNECT):
            #    yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
            #elif int(event.type) == int(enet.EVENT_TYPE_DISCONNECT):
            #    yeetable_event = (ykey, int(event.type), str(event.peer.address), None)
            #elif int(event.type) == int(enet.EVENT_TYPE_RECEIVE):
            #    yeetable_event = (ykey, int(event.type), str(event.peer.address), event.packet.data)

            inqueue.put(ipc_packet) #blocking ipc i guess!!!
    except KeyboardInterrupt:
        vile_semaphore[0]=1    #its our flag :)
        pass
    #finally:
    #    pass
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

        def ret_meta_error(ipc_err):
            ipc_err_pckt, prt_err = pref(sbytes("WRITTEN"), ("printable",repr(ipc_err)))
            responses.put(ipc_err_pckt)
            if prt_err:
                print("mprcs:enet_outbound:emergency meta-error failover print:%s:from:%s" % (prt_err,ipc_err))

        def serialize_IPC(fieldstring, pyobject):
            responses_ipc_packet, srlz_ipc_err = pref(sbytes(fieldstring), pyobject)
            if srlz_ipc_err:
                ret_meta_error(srlz_ipc_err)
            return responses_ipc_packet

        def deserialize_IPC(ipc_packet):
            pyobject, desrlz_ipc_err = pdref(ipc_packet)
            if desrlz_ipc_err:
                ret_meta_error(desrlz_ipc_err)
            return pyobject

        pflags = compose_bflags(
            [enet.PACKET_FLAG_UNSEQUENCED,
            enet.PACKET_FLAG_UNRELIABLE_FRAGMENT]
            )

        while run and semaphore_NOR(stopsema, vile_semaphore):       
            #unlimited block awaiting network outputs
            #sendable = outqueue.get()
            
            #refactor phase 1
            ipc_pckt = outqueue.get()
            sendable = deserialize_IPC(ipc_pckt)
            
            # sendable:(y_event[0],rpckt)   
            # evil_ass_kvstore identifier, protocol return packet
            
            #post-polling block;
            if sendable[0] == 'CHECKFLAG':
                #wake up blocked function
                continue
            #!REFACTOR WARNING!
            #this is the ONLY mechanism limiting infinite event table bloat??
            if sendable[1] is None:
                rspns_pckt = serialize_IPC("WRITTEN",("printable","purged None-returned entry from connection table."))
                responses.put(rspns_pckt)
                del evil_ass_kvstore[sendable[0]]
                continue

            event = evil_ass_kvstore[sendable[0]]
            payload = enet.Packet(sendable[1], pflags)
            #pflags specify unsequenced unreliable packet!
            
            #uses event.peer.send()?? not enet.peer.send()???
            #   🗡re: enet.pyx: ...
            sendstatus = event.peer.send(event.peer.incomingPeerID, payload)
            if sendstatus == -1 :
                printstring = "%s: uh oh in the echo packeto — intended payload was %s" % (str(event.peer.address), sendable[1][:80])
                printable = serialize_IPC("WRITTEN",("printable",printstring))
                responses.put(printable)
                del evil_ass_kvstore[sendable[0]]
                continue
            #printstring = "mprcs:enet_outbound:%s: chn:%s out: %r" % (str(event.peer.address), str(event.peer.incomingPeerID), sendable[1][:80])
            #responses.put(("printable",printstring))
            del evil_ass_kvstore[sendable[0]]
    except KeyboardInterrupt:
        vile_semaphore[1]=1    #its our flag :)
        pass
    #finally:
    #    pass
        #yeah idk what goes here

#PROTOCOL BLOCK
def blocky_printer(ipc_queues, vile_semaphore):
    try:
        run=True

        #inqueue = ipc_queues["sorites"]["bus"]
        #outqueue = ipc_queues["eubulides"]["bus"]
        responses = ipc_queues["responses"]["bus"]

        #FULLSTOP = vile_semaphore[4]
        #BLOCKY_PRINTER_STOP = vile_semaphore[2]
        stopsema = [4,2]
        while run and semaphore_NOR(stopsema, vile_semaphore):
            ipc_packet = responses.get()
            #print(repr(ipc_packet))
            printable, ipc_err = pdref(ipc_packet)
            if ipc_err:
                print("mprc:blocky_printer:unexpected IPC deserialization event:%s" % ipc_err)
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
    try:
        connect_count = 0
        run = True
        shutdown_recv = False

        inqueue = ipc_queues["sorites"]["bus"]
        outqueue = ipc_queues["eubulides"]["bus"]
        responses = ipc_queues["responses"]["bus"]

        def ret_meta_error(ipc_err):
            ipc_err_pckt, prt_err = pref(sbytes("WRITTEN"), ("printable",repr(ipc_err)))
            responses.put(ipc_err_pckt)
            if prt_err:
                print("mprcs:echo_protocol:emergency meta-error failover print:%s:from:%s" % (prt_err,ipc_err))

        def serialize_IPC(fieldstring, pyobject):
            responses_ipc_packet, srlz_ipc_err = pref(sbytes(fieldstring), pyobject)
            if srlz_ipc_err:
                ret_meta_error(srlz_ipc_err)
            return responses_ipc_packet

        def deserialize_IPC(ipc_packet):
            pyobject, desrlz_ipc_err = pdref(ipc_packet)
            if desrlz_ipc_err:
                ret_meta_error(desrlz_ipc_err)
            return pyobject

        #FULLSTOP = vile_semaphore[4]
        #ECHO_PROTOCOL_STOP = vile_semaphore[3]
        #while run and not (FULLSTOP or ECHO_PROTOCOL_STOP):
        stopsema = [4,3]
        while run and semaphore_NOR(stopsema, vile_semaphore):

            if connect_count <= 0 and shutdown_recv:
                printstring = "%s remaining sessions" % connect_count
                rspns_pckt = serialize_IPC("WRITTEN",("printable",printstring))
                responses.put(rspns_pckt)
                run = False
                continue

            #y_event = inqueue.get() #blocks until something is queued. 
            #y_event: (ykey, event.type, event.peer.address, event.packet.data.decode())

            #refactor phase 1
            #y_event, ipc_err = pdref(inqueue.get())
            #if ipc_err:
            #    ipc_err_pckt, prt_err = pref(sbytes("WRITTEN"), ("printable",repr(ipc_err)))
            #    responses.put(ipc_err_pckt)
            #    print("mprcs:echo_protocol:emergency meta-error failover print:%s:from:%s" % (prt_err,ipc_err_pckt))
            ipc_pckt = inqueue.get()
            y_event = deserialize_IPC(ipc_pckt)


            if y_event[0] == 'CHECKFLAG':
                continue

            if y_event[1] == int(enet.EVENT_TYPE_CONNECT):
                printstring ="%s: connecto" % y_event[2] # peer address
                rspns_pckt = serialize_IPC("WRITTEN",("printable",printstring))
                responses.put(rspns_pckt)
                #responses.put(("printable",printstring))
                connect_count +=1
                #purge evil_ass_kvstore event before y_event[0] reference expires
                nonsendable = serialize_IPC("EUBULIDES",(y_event[0],None))
                outqueue.put(nonsendable)

            elif y_event[1] == int(enet.EVENT_TYPE_DISCONNECT):
                printstring ="%s: unconnecto" % y_event[2] # peer address
                rspns_pckt = serialize_IPC("WRITTEN",("printable",printstring))
                responses.put(rspns_pckt)
                #responses.put(("printable",printstring))
                connect_count -=1
                #purge evil_ass_kvstore event before y_event[0] reference expires
                nonsendable = serialize_IPC("EUBULIDES",(y_event[0],None))
                outqueue.put(nonsendable)

            elif y_event[1] == int(enet.EVENT_TYPE_RECEIVE):
                #send (int channelID, Packet packet)
                rpckt = y_event[3]
                sendable = serialize_IPC("EUBULIDES",(y_event[0],rpckt))   #we can't presume a decoding bc non-utf8 bytes are possible
                #peer id key, echo packet. remember this is still only an echo server!
                #also remember to reencode that message to bytes. haha.
                outqueue.put(sendable)  #blocks until... outqueue is usable?
                if rpckt == b"SHUTDOWN":
                    shutdown_recv = True
                    printstring = "shutdown flag status: %s" % shutdown_recv
                    rspns_pckt = serialize_IPC("WRITTEN",("printable",printstring))
                    responses.put(rspns_pckt)
                printstring = "%s: out: %r" % (y_event[2], y_event[3][0:80])
                rspns_pckt = serialize_IPC("WRITTEN",("printable",printstring))
                responses.put(rspns_pckt)
                #responses.put(("printable",printstring))   #print safeguard
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

        #dont ask me why but signal interception is processwise and not threadwise.
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