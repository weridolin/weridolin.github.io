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


#### python threading local 的实现方式
直接上源码:

```python

class _localimpl:
    """A class managing thread-local dicts"""
    __slots__ = 'key', 'dicts', 'localargs', 'locallock', '__weakref__'

    def __init__(self):
        # The key used in the Thread objects' attribute dicts.
        # We keep it a string for speed but make it unlikely to clash with
        # a "real" attribute.
        self.key = '_threading_local._localimpl.' + str(id(self))

        # { id(Thread) -> (ref(Thread), thread-local dict) }
        self.dicts = {}   

    def get_dict(self):
        """Return the dict for the current thread. Raises KeyError if none
        defined."""
        thread = current_thread()
        return self.dicts[id(thread)][1] #  id(Thread) -> (ref(Thread), thread-local dict) 

    def create_dict(self):
        """Create a new dict for the current thread, and return it."""
        localdict = {}
        key = self.key
        thread = current_thread()
        idt = id(thread)
        def local_deleted(_, key=key):
            # When the localimpl is deleted, remove the thread attribute.
            thread = wrthread()
            if thread is not None:
                del thread.__dict__[key]
        def thread_deleted(_, idt=idt):
            # When the thread is deleted, remove the local dict.
            # Note that this is suboptimal if the thread object gets
            # caught in a reference loop. We would like to be called
            # as soon as the OS-level thread ends instead.
            local = wrlocal()
            if local is not None:
                dct = local.dicts.pop(idt)
        wrlocal = ref(self, local_deleted)
        wrthread = ref(thread, thread_deleted)
        thread.__dict__[key] = wrlocal ## 报local作为弱引用赋值给 thread.__dict__
        self.dicts[idt] = wrthread, localdict
        return localdict


@contextmanager
def _patch(self):
    impl = object.__getattribute__(self, '_local__impl')
    try:
        dct = impl.get_dict() ## 从 IMPL中根据线程id从 impl._local__impl.dicts 获取到对应的 dict 
    except KeyError:
        dct = impl.create_dict() # 没有则创建一个新的dict
        args, kw = impl.localargs
        self.__init__(*args, **kw)
    with impl.locallock:
        object.__setattr__(self, '__dict__', dct) # 这里把 local object的 __dict__指向 dct. attr操作都是对 __dict__ ,即对 dct 操作
        yield


class local:
    __slots__ = '_local__impl', '__dict__'

    def __new__(cls, /, *args, **kw):

        ### _local__impl 才是实际储存的实现

        if (args or kw) and (cls.__init__ is object.__init__):
            raise TypeError("Initialization arguments are not supported")
        self = object.__new__(cls)
        impl = _localimpl()
        impl.localargs = (args, kw)
        impl.locallock = RLock() # 设置值时必须 互che
        object.__setattr__(self, '_local__impl', impl)
        # We need to create the thread dict in anticipation of
        # __init__ being called, to make sure we don't call it
        # again ourselves.
        impl.create_dict()
        return self

    def __getattribute__(self, name):
        with _patch(self):
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only"
                % self.__class__.__name__)
        with _patch(self):
            return object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only"
                % self.__class__.__name__)
        with _patch(self):
            return object.__delattr__(self, name)


```

从源码可知，实际的储存结构为: local 实例 -->  _local__impl --> map [thread id]，一个local根据不同线程在`_local__impl.map`中创建对应的key-value.对`local`对象设置值和赋值，删除值等操作时，会先把`local.__dict__`指向对应的` _local__impl.map[thread-id]`,这才是实际操作的字典。