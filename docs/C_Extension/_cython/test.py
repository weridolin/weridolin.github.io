def mouse_hook_callback(mouse_event):
    print(f"i am mouse hook call back:{mouse_event}")
    return False

def keyboard_hook_callback(kb_virtual_code):
    print(f"i am keyboard call back:{kb_virtual_code}")
    return False

import hook,time,threading

def start():
    hook.add_keyboard_hook_callback(keyboard_hook_callback)
    hook.install_keyboard_hook()
    hook.start_hook()
    # for i in range(5):
    #     time.sleep(1)

t = threading.Thread(target=start,args=())
t.daemon = True
t.start()
for i in range(10):
    time.sleep(1)
    print("ss")