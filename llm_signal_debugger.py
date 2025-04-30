#```python
import signal
import time
import multiprocessing
import sys

def exccatcher(sigsigdotsigdotsigtype, fn, *args, **kwargs):
    #pass list of tuples of signal.signal(signal.SIGINT, signal_handler) args
    print(sigsigdotsigdotsigtype)
    for sigdotsigtype in sigsigdotsigdotsigtype:
        print(sigdotsigtype)
        signal.signal(sigdotsigtype[0], sigdotsigtype[1])
    #how many signals should we handle? all of them!
    try:
        fn(*args,**kwargs)
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt)):
            print(f"that exception vibed like term request!!!")
            args[0].set()
            pass
        #pass if ur evil raise if ur good
        raise

def signal_handler(signum, frame):
    """Handles the SIGINT (Ctrl+C) signal."""
    print(f"Received {signum}! raising poopdick!")
    raise KeyboardInterrupt("POOPDICK received!!\n im a very serious core programmer and my interrupt signal is called POOPDICK!!!!")
    # In a real application, you'd trigger your interrupt scheduler here.
    # This example just sets a global flag.
    """
    global shutdown_flag
    global shutdown_event
    shutdown_flag = True
    print(f"shutflag?{shutdown_flag}")
    shutdown_event.set()
    print(f"shutdowneventisset?{shutdown_event.is_set()}")
    """

"""
def worker_process(shutdown_event):
    signal.signal(signal.SIGINT, signal_handler)
    #Simulates a long-running process that checks for shutdown signals.
    print("Worker process started.")
    #global shutdown_flag
    try:
        while not shutdown_event.is_set():
            print("Worker process doing work...")
            print(f"shutdowneventisset?{shutdown_event.is_set()}")
            time.sleep(2)  # Simulate work
    except KeyboardInterrupt:
        # This exception will not be raised if signal is caught by the main process
        print("worker process received errant KeyboardInterrupt...?  Shutting down.../n it's not it's it's not shutting down it's [KLAXON NOISES]")
        pass  # or log it, but it's handled at the signal handler level.
    finally:
        print("Worker process shutting down gracefully.")
"""

def worker_process(shutdown_event):
    print("Worker process started.")
    try:
        while not shutdown_event.is_set():
            print("Worker process doing work...")
            print(f"shutdowneventisset?{shutdown_event.is_set()}")
            time.sleep(2)  # Simulate work
    except KeyboardInterrupt:
        # This exception will not be raised if signal is caught by the main process
        print("worker process received errant KeyboardInterrupt...?  Shutting down.../n it's not it's it's not shutting down it's [KLAXON NOISES]")
        pass  # or log it, but it's handled at the signal handler level.
    finally:
        print("Worker process shutting down gracefully.")

if __name__ == "__main__":
    # Register the SIGINT handler.
    signal.signal(signal.SIGINT, signal_handler)
    #ssdsdst= ((signal.SIGINT, signal_handler),(signal.SIGTERM, signal_handler))
    #always pass as a tuple even if its a tuple of 1 item
    ssdsdst= ((signal.SIGINT, signal_handler),)


    # Shared event to signal the worker process to shut down.  Use multiprocessing.Event
    # instead of a simple boolean, so the shutdown is reliable.
    shutdown_event = multiprocessing.Event()
    global shutdown_flag
    shutdown_flag = False #redundant with shutdown_event but for clarity

    # Create the process.
    #process = multiprocessing.Process(target=worker_process, args=(shutdown_event,))
    process = multiprocessing.Process(target=exccatcher, args=(ssdsdst, worker_process, shutdown_event,))
    try:
        process.start()
        #...
        process.join()
    except KeyboardInterrupt:
        # This exception will not be raised if signal is caught by the main process
        print("caught KeyboardInterrupt...?  Shutting down.../n it's not it's it's not shutting down it's [KLAXON NOISES]")
        shutdown_event.set()
        #pass  # or log it, but it's handled at the signal handler level.
    finally:
        print("Worker process shutting down gracefully.")




    print("Program finished.")
#```
