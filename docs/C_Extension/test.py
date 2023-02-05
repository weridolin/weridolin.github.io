
import threading
import hook 
import time
from functools import lru_cache

def keyboard_callback(kb_virtual_code:int):
    """
        kb_virtual_code:按下键盘对应的键盘码.参考 windows api
        return:
            True:结束这次事件
            False:屏蔽这次键盘事件
    
    """
    print(f"i am keyboard callback:{kb_virtual_code}")
    return False

def mouse_callback(mouse_event:int):
    """
        mouse_event:按下键盘对应的事件.参考 windows api
        return:
            True:结束这次事件·
            False:屏蔽这次鼠标事件
    
    """
    print(f"i am mouse callback:{mouse_event}")
    return False

def stop_hook(hook_running_thread_id=None):
    assert hook_running_thread_id is not None,"hook running thread id can not be None"
    hook.stop(hook_running_thread_id)
    
def start():
    print(dir(hook))
    hook.add_keyboard_hook_cb(keyboard_callback)
    hook.install_keyboard_hook()
    # hookE.add_mouse_hook_cb(mouse_callback)
    # hookE.install_mouse_hook()
    hook.start()
    # for i in range(10):
    #     print("ttt")
    #     time.sleep(1)

t = threading.Thread(target=start,args=())
t.daemon=False
t.start()
time.sleep(2)
stop_hook(t.native_id)
for i in range(1):
    # print("2222222ssssssss")
    time.sleep(1)


