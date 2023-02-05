#include <stdio.h>
#include <stdlib.h>
#include <Windows.h>
#include <WinUser.h>
#pragma comment(lib, "user32.lib") // 真正实现SetWindowsHookEx的方法

/*
    windows消息队列:
        鼠标/键盘事件  ---> 系统消息队列  ---->   [hook1,hook2....](钩子链)  ----> 应用程序消息队列
*/

// 钩子
static HHOOK mouse_hook = NULL;
static HHOOK keyboard_hook = NULL;

typedef int (*callback)(WPARAM wParam);
callback mouse_hook_cb = NULL;
callback keyboard_hook_cb = NULL;


// mouse hook callback
LRESULT CALLBACK KeyBoardProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    /* ll
        typedef struct tagKBDLLHOOKSTRUCT {
        DWORD     vkCode;		// 按键代号
        DWORD     scanCode;		// 硬件扫描代号，同 vkCode 也可以作为按键的代号。
        DWORD     flags;		// 事件类型，一般按键按下为 0 抬起为 128。
        DWORD     time;			// 消息时间戳
        ULONG_PTR dwExtraInfo;	// 消息附加信息，一般为 0。
        }KBDLLHOOKSTRUCT,*LPKBDLLHOOKSTRUCT,*PKBDLLHOOKSTRUCT;
    */
    KBDLLHOOKSTRUCT *ks = (KBDLLHOOKSTRUCT *)lParam;
    printf("get keyboard event :%I64i \n", wParam);
    // 调用PYTHON 回调函数处理
    BOOL ignore=FALSE;  
    ignore = keyboard_hook_cb(wParam);
    if (!ignore)
    {
        return CallNextHookEx(NULL, nCode, wParam, lParam);
    }
    else
    {
        printf("ignore this keyboard event");
        return 1;
    }
}

// mouse hook处理函数
LRESULT CALLBACK MouseProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    /*
    typedef struct tagMOUSEHOOKSTRUCT {
        POINT   pt;					// Point数据
        HWND    hwnd;				// 接收鼠标消息的窗体的句柄
        UINT    wHitTestCode;		// 指定点击测试值
        ULONG_PTR dwExtraInfo;		// 指定和该消息相关联的附加信息。
    } MOUSEHOOKSTRUCT, FAR* LPMOUSEHOOKSTRUCT, * PMOUSEHOOKSTRUCT;
    */

    MOUSEHOOKSTRUCT *ms = (MOUSEHOOKSTRUCT *)lParam;
    printf("get keyboard event :%I64i \n", wParam);

    // 调用PYTHON 回调函数处理
    BOOL ignore = FALSE;
    ignore = mouse_hook_cb(wParam);
    if (!ignore)
    {
        return CallNextHookEx(NULL, nCode, wParam, lParam);
    }
    else
    {
        printf("ignore this mouse event");
        return 1;
    }
}

// python函数作为回调参数
BOOL AddMouseHookCallbackFunc(callback cb)
{
    mouse_hook_cb = cb;
    return TRUE;
}

// python函数作为回调参数
BOOL AddKeyBoardCallbackFunc(callback cb)
{
    printf("add keyboard callback \n");
    // cb(111111111);
    keyboard_hook_cb = cb;
    // keyboard_hook_cb(WM_MBUTTONUP);
    return TRUE;
}

BOOL InstallMouseHook()
{
    if (mouse_hook_cb == NULL)
    {
        // PyErr_SetString(PyExc_TypeError, "please add mouse hook callback first!");
        return FALSE;
    }
    HINSTANCE hk = GetModuleHandle(NULL);                         // NULL则会返回当前进程ID
    mouse_hook = SetWindowsHookEx(WH_MOUSE_LL, MouseProc, hk, 0); // WH_MOUSE_LL表示全局键盘钩子
    return TRUE;
}

BOOL InstallKeyBoardHook()
{
    printf("thread id in install func:%i \n", GetCurrentThreadId());
    if (keyboard_hook_cb == NULL)
    {
        // PyErr_SetString(PyExc_TypeError, "please add keyboard hook callback first!");
        return FALSE;
    }
    HINSTANCE hk = GetModuleHandle(NULL);                                  // NULL则会返回当前进程ID
    keyboard_hook = SetWindowsHookEx(WH_KEYBOARD_LL, KeyBoardProc, hk, 0); // WH_KEYBOARD_LL表示全局键盘钩子
    return TRUE;
}

// start hook
BOOL start()
{
    MSG msg;
    BOOL bRet;
    if (mouse_hook == NULL && keyboard_hook == NULL)
    {
        // PyErr_SetString(PyExc_TypeError, "please START HOOK first!");
        // return NULL;
        return FALSE;
    }
    while (bRet = GetMessageW(&msg, NULL, 0, 0) != 0)
    {
        if (bRet == -1)
        {
            // handle the error and possibly exit
            printf("error ---> getMessage error");
        }
        else
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }
    printf("stop hook....");
    UnhookWindowsHookEx(mouse_hook);
    return TRUE;
}

// stop hook
BOOL stop(unsigned long t_id)
{
    if (mouse_hook == NULL && keyboard_hook == NULL)
    {
        // PyErr_SetString(PyExc_TypeError, "please START HOOK first!");
        // return NULL;
        return FALSE;
    }
    PostThreadMessageW(t_id, WM_QUIT, 0, 0);
    return TRUE;
}

void hello(char *name)
{
    printf("hello name %s", name);
}