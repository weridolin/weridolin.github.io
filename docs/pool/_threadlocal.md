### threading local
简单来说,threading local是一个线程隔离的存储结构,每一个local()对象中的数据在不同的线程中互相不干扰。其内部实现只要是以一个线程id为key的map来实现的.结构如下:    

```python

    #  local-instance._local__impl.map 结构
    { id(Thread)s:(ref(Thread), thread-local dict) }

```
即如果实例化了 ctx = local().并且同时用于 thread1,thread2. 则有 ctx._local__impl.map为：{id(thread1)s: (ref(thread1), {}),id(thread2)s: (ref(thread2), {})}.
即为每一个local实例，都会在对应的_local__impl.map中创建对应的*d(Thread)s:(ref(Thread), thread-local dict)*


```python

    import threading

    ctx = threading.local()
    ctx.var1="Var1"
    ctx.var2="Var2"
    print(ctx.__dict__)

    def f():
        # ctx.var1="Var11"
        # ctx.var2="Var22"
        print(ctx)
        print(ctx.__dict__)

    threading.Thread(target=f).start()

    >>> 输出:
    >>>  {'var1': 'Var1', 'var2': 'Var2'} ## main thread
    >>>  {}                               ## another thread

```



