from concurrent.futures import ThreadPoolExecutor,as_completed, thread
import threading
import time,datetime

event  = threading.Event()

def task(seconds):
    print(">>>",seconds)
    # event = threading.Event()
    # event.wait(10)
    time.sleep(2)


def wakeup():
    print("wake up")
    event.set()


if __name__ =="__main__":
    pool = ThreadPoolExecutor(max_workers=1)
    futs = []
    # for i in range(0,10,2):
    #     fut = pool.submit(task,i)
    #     futs.append(fut)
    pool.submit(task,22)
    time.sleep(2)
    pool.submit(wakeup)
    
    res = as_completed(futs)
    # for r in res:
    #     print(datetime.datetime.now())
    #     print(r)
    #     print(datetime.datetime.now())
  