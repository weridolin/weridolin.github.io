from threading import  Semaphore
from threading import Condition,Thread
import threading
import time
from functools import partial

# def child(condition:Condition,index):
#     with condition:
#         print("get condition",threading.current_thread(),"beign to wait")
#         # condition.wait_for(predicate=partial(wait_for_condition,index))
#         condition.wait()
#         # print(condition._waiters)
#         time.sleep(2)
#         print("get condition",threading.current_thread(),"awake")
#         time.sleep(2)

# def wait_for_condition(index):
#     print(">>> check index",index)
#     if index>=2:
#         return False
#     else:
#         return True

# def child(semaphore:Semaphore,index):
#     print("get condition",threading.current_thread(),"beign to wait")
#     with semaphore:
#         print("get condition",threading.current_thread(),"awake ")
#         time.sleep(2)

def child(lock,index):
    if index ==0:
        lock.release()
    print("get condition",threading.current_thread(),"begin to wait")
    with lock:
        print("get condition",threading.current_thread(),"awake ")
        time.sleep(2)

if __name__ == "__main__":
    con = threading.Condition(threading.RLock())
    con.acquire()
    sem = threading.Semaphore(0)
    lock = threading.RLock()
    lock.acquire() 
    # lock.acquire()   
    for i in range(4):
        t = Thread(target=child,args=(con,i))
        t.start()
    time.sleep(2)
    # lock.release()
    # lock.release()
    # con.notify_all()
    # with con:
    #     # con.notify_all()
    #     con.notify()

    # time.sleep(3)
    # with con:
    #     con.notify_all()
