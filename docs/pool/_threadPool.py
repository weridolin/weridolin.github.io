from concurrent.futures import ThreadPoolExecutor,as_completed

import time,datetime

def task(seconds):
    time.sleep(seconds)


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