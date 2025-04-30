#KONKUR.py
import threading
import struct
import multiprocessing

#AIIEEIEIEIIEEIEIEEEEEEE

def main():
    sfstr = "4c"
    #pytype 'byte' x4
    s=struct.pack(sfstr,b"s",b"u",b"s",b"!")
    print(struct.unpack(sfstr,s))
    
    print("circuit alive?")
    print(True and not (False or False or False or False or True))

    v_semaphore = multiprocessing.Array('i', 5, lock=False)

    alias_1 = v_semaphore[:1]
    alias_2 = v_semaphore[4:5]

    idx= [i for i in range(5)]
    val= [i for i in range(20,25,1)]

    zuple=list(zip(idx,val))
    print(zuple)
    #print(f"{[*zuple][0]},{[*zuple][1]}")
    for zop in list(zuple):
        v_semaphore[zop[0]]=zop[1] 
    print(*v_semaphore)
    print(f"{alias_1},{v_semaphore[:1]}")
    print(f"{alias_2},{v_semaphore[4:5]}")


    #lock.acquire()
    #try:
    #    ...
    #finally:
    #    lock.release()

if __name__ == '__main__':
    main()

#def sighandle():

#def stop():

