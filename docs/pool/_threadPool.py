from concurrent.futures import ThreadPoolExecutor,as_completed, thread
import threading
import time,datetime

def task(seconds):
    time.sleep(10)


if __name__ =="__main__":
    pool = ThreadPoolExecutor()
    futs = []
    for i in range(0,10,2):
        fut = pool.submit(task,i)
        futs.append(fut)
    
    
    res = as_completed(futs,timeout=5)
    for r in res:
        print(datetime.datetime.now())
        print(r)
        print(datetime.datetime.now())
  