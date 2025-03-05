import os
import threading, time

def tx():
    os.system("python3 test/tx.py")

def rx():
    os.system("python3 test/rx.py")

def main():
    for i in range(1000):
        t1 = threading.Thread(target=rx)
        t2 = threading.Thread(target=tx)
 

        t2.start()
        time.sleep(.1)
        t1.start()

        t1.join()
        t2.join()

        t1 = None
        t2 = None

if __name__ == "__main__":
    main()