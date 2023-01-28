#include <stdio.h>
#include <stdlib.h>
#include <Python.h>
#include <Windows.h>
#include <WinUser.h>
#pragma comment(lib, "user32.lib") // 真正实现SetWindowsHookEx的方法

/*
    windows消息队列:
        鼠标/键盘事件  ---> 系统消息队列  ---->   [hook1,hook2....](钩子链)  ----> 应用程序消息队列
*/

// 钩子
static HHOOK g_hook = NULL;
static PyObject *mouse_hook_cb = NULL;

int InvokeMouseHookCallBack()
{
    if (!PyCallable_Check(mouse_hook_cb))
    {
        PyErr_SetString(PyExc_TypeError, "mouse hook callback is not callable");
        return -1;
    }
    else
    {
        printf(">>> call mouse hook callback");
        PyObject_CallFunction(mouse_hook_cb, NULL);
        return 1;
    }
}

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
    // if (wParam == WM_KEYDOWN)
    // {
    //     printf("keyboard press down");
    // }
    // else
    if (wParam == WM_KEYUP)
    {
        printf("keyboard press up");
        int res = InvokeMouseHookCallBack();
        if (res == -1)
        {
            printf(">>> exec callback fun error");
        }
    }
    // return 1;	// 吃掉消息
    return CallNextHookEx(NULL, nCode, wParam, lParam);
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

    printf(">>> mouse  event get");
    // return 1;	// 吃掉消息
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

// python函数作为回调参数
static PyObject *AddMouseHookCallbackFunc(PyObject *self, PyObject *args)
{
    // static PyObject *callback = NULL;
    if (PyArg_ParseTuple(args, "O:set_callback", &mouse_hook_cb))
    {
        if (!PyCallable_Check(mouse_hook_cb))
        {
            PyErr_SetString(PyExc_TypeError, "param is not callable");
            return PyBool_FromLong(1);
        }
        else
        {
            printf(">>> add mouse hook callback");
            // PyObject_CallFunction(mouse_hook_cb, NULL);
            return PyBool_FromLong(1);
        }
    }
    return PyBool_FromLong(1);
}

static PyObject *InstallMouseHook(PyObject *self)
{
    if (mouse_hook_cb == NULL)
    {
        PyErr_SetString(PyExc_TypeError, "please add mouse hook callback first!");
        return NULL;
    }
    HINSTANCE hk = GetModuleHandle(NULL); //NULL则会返回当前进程ID
    g_hook = SetWindowsHookEx(WH_KEYBOARD_LL, KeyBoardProc, hk, 0); //WH_KEYBOARD_LL表示全局键盘钩子 
    return PyBool_FromLong(1);
}

static PyObject *start(PyObject *self)
{
    if (g_hook == NULL)
    {
        PyErr_SetString(PyExc_ValueError, "please install hook first");
        return NULL;
    }
    MSG msg;

    HINSTANCE hk = GetModuleHandle(NULL); //NULL则会返回当前进程ID TODO 1.getMessage 加hk参数  2.用peekMessage
    printf(GetMessage(&msg, hk, 0, 0));
	// while (TRUE)
	// {   
    //     // printf("get message");
	// 	// TranslateMessage(&msg);
	// 	// DispatchMessage(&msg);
    //     Sleep(100);
	// }

    UnhookWindowsHookEx(g_hook);

    return PyBool_FromLong(1);
}

// e-extension相关的初始函数，包括c-extension里面对应函数和模块信息

// 方法信息，可以包含多个方法
static PyMethodDef HookMethods[] = {
    {"install_mouse_hook",  // PYthon调用时对应的方法
     InstallMouseHook,      // 对应的C-EXTENSION里面的方法
     METH_NOARGS,           // 标记,告诉PYTHON解释器这个方法无参数
     "install mouse hook"}, // 函数说明
    {
        "start",       // PYthon调用时对应的方法
        start,               // 对应的C-EXTENSION里面的方法
        METH_NOARGS,         // 标记,告诉PYTHON解释器这个方法无参数
        "start mouse hook"}, // 函数说明
    {
        "add_mouse_hook_cb",                 // PYthon调用时对应的方法
        AddMouseHookCallbackFunc,            // 对应的C-EXTENSION里面的方法
        METH_VARARGS,                        // 标记,告诉PYTHON解释器有位置参数
        "add mouse hook callback function"}, // 函数说明
    {NULL, NULL, 0, NULL}                    // 一定要加上这个，否则pyd无法正常导入
};

// module信息
static struct PyModuleDef HookModule = {
    PyModuleDef_HEAD_INIT,
    "hookE",                            // module name
    "python hook api from c extension", // module docstring
    -1,                                 // ？
    HookMethods                         // 该module对应的方法列表
};

// PyMODINIT_FUNC：python import时运行的方法 PyInit_{{module name}}
PyMODINIT_FUNC PyInit_hookE(void)
{
    PyObject *module = PyModule_Create(&HookModule);
    return module;
}

// int main(void)
// {
//     // FILE *fp = fopen("write.txt", "w");
//     // fputs("Real Python!", fp);
//     // fclose(fp);
//     // return 1;
// 	// 消息循环是必须的，Windows直接在你自己的进程中调用你的hook回调.要做这个工作,
// 	//需要一个消息循环.没有其他机制可以让您的主线程进行回调,
// 	//回调只能在您调用Get / PeekMessage()以使Windows可以控制时发生.
//     // InstallHook();
// 	// MSG msg;
// 	// while (GetMessage(&msg, NULL, 0, 0))
// 	// {
// 	// 	TranslateMessage(&msg);
// 	// 	DispatchMessage(&msg);
// 	// }

// 	// UnhookWindowsHookEx(g_hook);

// 	return 0;

// }