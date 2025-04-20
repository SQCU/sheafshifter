#pyenet_serv
import sys, os
import enet

#empty project template doesn't have any control flow to keep enet host alive w.
#re: readme.md notes, 
#we need  control flow calling enet_host_service()
#to actually do anything with enet, incl. testing it

#okay we implemented a control circuit which takes a stream of bytearrays!
#last big mystery for the synchronous monoconnection program is the double print
#unconnecto /n unconnecto.
#mystery solved!

def main():
    host = enet.Host(enet.Address("localhost", 33333), 10, 0, 0, 0)
    host.checksum = enet.ENET_CRC32
    connect_count = 0
    run = True
    shutdown_recv = False

    while run:
        #check immediately for EnvironmentError
        event = host.service(0) # wait 250ms for network activity
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


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Explicitly interrupted')
        sys.exit(130)