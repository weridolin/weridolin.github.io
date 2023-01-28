#include <stdio.h>
#include <stdlib.h>
#include <process.h>
#include <io.h>
//必须将包含的python.h添加到GCC对应的环境变量中
#include <Python.h>
#define FPUTS_MACRO 256

// int main(void)
// {
//     // FILE *fp = fopen("write.txt", "w");
//     // fputs("Real Python!", fp);
//     // fclose(fp);
//     // return 1;
//     printf(">>>");
// }
// 在python中，所有的一切皆为对象,所有的对象继承于PyObject,
// 在C-extension中，对应的返回值，参数也都为 PyObject
//  C <--- PyObject ---> python
static PyObject *method_fputs(PyObject *self, PyObject *args)
// 函数 method_fputs,返回一个指针，指向一个PyObject对象 
{

    char *str, *filename = NULL;
    int bytes_copied = -1;

    /* Parse arguments */
    // PyArg_ParseTuple获取从python传过来的参数
    // ss代表参数为字符串
    // @https://docs.python.org/3/c-api/arg.html
    if (!PyArg_ParseTuple(args, "ss", &str, &filename))
    {
        return NULL; // 返回 NULL -1 表示异常
    }   

    if (strlen(str)<10){
        PyErr_SetString(PyExc_ValueError,"长度不能小于10ss!!!1!！！ss");//todo 中文结尾的报错问题 C2001 C2143
        return NULL;
    }

    FILE *fp = fopen(filename, "w");
    bytes_copied = fputs(str, fp);
    fclose(fp);
    // 返回一个PyLongObject,对应者python里面的integer对象
    return PyLong_FromLong(bytes_copied);
}

static PyObject *raise_custom_err(PyObject *self,PyObject *args){
    // PyErr_sets
}

// e-extension相关的初始函数，包括c-extension里面对应函数和模块信息

// 方法信息，可以包含多个方法
static PyMethodDef FputsMethods[] = {
    {  "fputs", // PYthon调用时对应的方法
        method_fputs, // 对应的C-EXTENSION里面的方法
        METH_VARARGS, // 标记,告诉PYTHON解释器将会接受2个PyObject参数
        "Python interface for fputs C library function"
    },//函数说明
    {NULL, NULL, 0, NULL}
};


// module信息
static struct PyModuleDef fputsmodule = {
    PyModuleDef_HEAD_INIT,
    "fputs", //module name
    "Python interface for the fputs C library function", //module docstring
    -1,//？
    FputsMethods //该module对应的方法列表
};

// 自定义异常
// static PyObject *MyError = NULL;

// PyMODINIT_FUNC:python import时运行的方法 PyInit_{{module name}}
PyMODINIT_FUNC PyInit_fputs(void) {
    PyObject *module =  PyModule_Create(&fputsmodule);
    //定义一个自定义异常
    PyObject *MyError = PyErr_NewException("fputs.MyError", NULL, NULL);
    // 把该异常添加到 module object里面
    PyModule_AddObject(module,"MyError",MyError);
    // 增加一个整形常量
    PyModule_AddIntConstant(module, "FPUTS_FLAG", 64);
    // 增加一个宏定义
    PyModule_AddIntMacro(module,FPUTS_MACRO);
    // 
    return module;
}

