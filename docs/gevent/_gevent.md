## 什么是gevent？
在python自带的异步模块asynico出来之前,gevent是一个支持协程的python库,其基于**libev**or**libuv**实现了python的协程.gevent将python的一些I/O内置库,比如socket/select/threading/subprocess等.每一个I/O操作会被封装成一个支持的异步的greenlet(相当于asyncio的task),然后自身实现的事件循环loop进行驱动


## monkey patch
在异步模块asynico出来之前,由于python内置的I/O库无法支持异步，所以gevent自身把python相关的网络库改写成了支持的异步,使用了monkey patch后,import相关的库实际上会import了gevent改写后的对应的库