# import fputs
# import os,sys
# print(dir(fputs),fputs)
# path = os.path.join(os.path.dirname(__file__),"test.txt")
# fputs.fputs("是",path)
# print(fputs.MyError,fputs.FPUTS_FLAG,fputs.FPUTS_MACRO)
import time

def callback():
    print("i am callback")


# import hookE
# print(">>>")
# print(hookE,dir(hookE))
# hook.call(callback)()

import threading

def start():
    for i in range(5):
        print(">>>>")
        time.sleep(1)


t = threading.Thread(target=start,args=())
t.daemon=True
t.start()
# t.join()

import hookE
hookE.add_mouse_hook_cb(callback)
hookE.install_mouse_hook()
hookE.start()

for i in range(5):
    print("2222222ssssssss")
    import time
    time.sleep(1)
# while input()!="q":
    # continues