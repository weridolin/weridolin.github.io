import fputs
# import os,sys,threading,time
# def async_func():
#     path = os.path.join(os.path.dirname(__file__),"test.txt")
#     fputs.loop()


# t = threading.Thread(target=async_func,args=())
# t.daemon=False
# t.start()
# for i in range(10):
#     print("222")
#     time.sleep(1)
# t.join()
import time

def keyboard_callback(kb_virtual_code:int):
    """
        kb_virtual_code:按下键盘对应的键盘码.参考 windows api
        return:
            True:结束这次事件
            False:继续调用接下来的事件
    
    """
    print(f"i am keyboard callback:{kb_virtual_code}")
    return False

def mouse_callback(mouse_event:int):
    """
        mouse_event:按下键盘对应的事件.参考 windows api
        return:
            True:结束这次事件·
            False:继续调用接下来的事件
    
    """
    print(f"i am mouse callback:{mouse_event}")
    return False


import threading
import hookE 

def start():
    print(dir(hookE))
    hookE.add_keyboard_hook_cb(keyboard_callback)
    hookE.install_keyboard_hook()
    # hookE.add_mouse_hook_cb(mouse_callback)
    # hookE.install_mouse_hook()
    hookE.start()
    # for i in range(10):
    #     print("ttt")
    #     time.sleep(1)

t = threading.Thread(target=start,args=())
t.daemon=False
t.start()
time.sleep(2)
hookE.stop(t.native_id)
for i in range(1):
    # print("2222222ssssssss")
    time.sleep(1)

# 因为是线程启动，停止的时候需要传一个线程ID进去

