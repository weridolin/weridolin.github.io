from threading import Condition,Thread
import threading
import time
from functools import partial

def child(condition:Condition,index):
    with condition:
        print("get condition",threading.current_thread(),"beign to wait")
        condition.wait_for(predicate=partial(wait_for_condition,index))
        # print(condition._waiters)
        time.sleep(2)
        print("get condition",threading.current_thread(),"awake ")
        time.sleep(2)

def wait_for_condition(index):
    print(">>> check index",index)
    if index>=2:
        return False
    else:
        return True


if __name__ == "__main__":
    con = threading.Condition()
    for i in range(4):
        t = Thread(target=child,args=(con,i))
        t.start()
    time.sleep(2)
    # con.notify_all()
    with con:
        con.notify_all()

    time.sleep(3)
    with con:
        con.notify_all()
