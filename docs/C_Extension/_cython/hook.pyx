## 注意访问 python 对象时必须为获取到GIL的状态！
## CYTHON也不会自动释放GIL
cdef extern from "chook.c":
    ctypedef unsigned long WPARAM;
    ctypedef int BOOL;
    ctypedef int (*callback)(WPARAM wParam);
    void hello(char *name);
    BOOL start(); # 
    BOOL stop(unsigned long t_id);
    BOOL InstallMouseHook();
    BOOL InstallKeyBoardHook();
    BOOL AddMouseHookCallbackFunc(callback); 
    BOOL AddKeyBoardCallbackFunc(callback);
    
cdef extern from "Windows.h":
    pass

cdef extern from "WinUser.h":
    pass
    

cdef object kb_cb_func;
cdef object mouse_cb_func;

def start_hook():
    res = start() #这里不能直接 return _start()? #TODO
    return res

def stop_hook(thread_id:int):
    return stop(thread_id)

def install_mouse_hook():
    return InstallMouseHook()

def install_keyboard_hook():
    return InstallKeyBoardHook()

def add_mouse_hook_callback(cb_func):
    global mouse_cb_func
    mouse_cb_func =cb_func
    return AddMouseHookCallbackFunc(_mouse_cb_wrapper)

def add_keyboard_hook_callback(cb_func):
    global kb_cb_func
    kb_cb_func = cb_func
    print(">>> add callback",kb_cb_func)
    return AddKeyBoardCallbackFunc(_kb_hook_cb_wrapper)

cdef int _kb_hook_cb_wrapper(wParam:WPARAM):
    print(">>call callback in wrapper")
    global kb_cb_func
    return kb_cb_func(wParam)
    return 0


cdef int _mouse_cb_wrapper(wParam:WPARAM):
    global mouse_cb_func
    return mouse_cb_func(wParam)



