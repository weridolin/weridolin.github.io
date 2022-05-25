## future
在线程中，future表示一个task的执行结果.当调用线程池的*submit*后.会返回一个future.线程池的执行结果都会封装在*future*里面。有点类似协程中的*future*

## worker
*worker*是线程池中实际运行的函数.每个*worker*都会从*worker_queue*(所有worker共享,存放实际运行的task)中获取用户提交的task并运行。    
```python
def _worker(executor_reference, work_queue, initializer, initargs):
    # worker初始化
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical('Exception in initializer:', exc_info=True)
            executor = executor_reference()
            if executor is not None:
                executor._initializer_failed()
            return
    try:
        while True:
            # 不断从 work_queue 获取任务执行
            work_item = work_queue.get(block=True)
            if work_item is not None:
                work_item.run()
                # Delete references to object. See issue16284
                del work_item

                # attempt to increment idle count
                executor = executor_reference()
                if executor is not None:
                    executor._idle_semaphore.release() # 释放 _idle_semaphore
                del executor
                continue
            
            ## 为None。结束worker线程
            executor = executor_reference()
            # Exit if:
            #   - The interpreter is shutting down OR
            #   - The executor that owns the worker has been collected OR
            #   - The executor that owns the worker has been shutdown.
            if _shutdown or executor is None or executor._shutdown:
                # Flag the executor as shutting down as early as possible if it
                # is not gc-ed yet.
                if executor is not None:
                    executor._shutdown = True
                # Notice other workers
                work_queue.put(None)
                return
            del executor
    except BaseException:
        _base.LOGGER.critical('Exception in worker', exc_info=True)
```


## worker_item
对用户提交函数的封装,包括运行的函数，入参，存放结果的*future*等.源码如下:       
```python

    class _WorkItem(object):
        def __init__(self, future, fn, args, kwargs):
            self.future = future # 存放运行的结果
            self.fn = fn # 运行的函数
            self.args = args # 
            self.kwargs = kwargs

        def run(self):
            if not self.future.set_running_or_notify_cancel():
                return

            try:
                result = self.fn(*self.args, **self.kwargs)
            except BaseException as exc:
                self.future.set_exception(exc)
                # Break a reference cycle with the exception 'exc'
                self = None
            else:
                self.future.set_result(result)
  
        __class_getitem__ = classmethod(types.GenericAlias)


```


## ThreadPoolExecutor

先看python中ThreadPoolExecutor的源码    

```python

class ThreadPoolExecutor(_base.Executor):

    # Used to assign unique thread names when thread_name_prefix is not supplied.
    _counter = itertools.count().__next__

    def __init__(self, max_workers=None, thread_name_prefix='',
                 initializer=None, initargs=()):
        """Initializes a new ThreadPoolExecutor instance.

        Args:
            max_workers: The maximum number of threads that can be used to
                execute the given calls.
            thread_name_prefix: An optional name prefix to give our threads.
            initializer: A callable used to initialize worker threads.
            initargs: A tuple of arguments to pass to the initializer.
        """
        if max_workers is None:
            # ThreadPoolExecutor is often used to:
            # * CPU bound task which releases GIL
            # * I/O bound task (which releases GIL, of course)
            #
            # We use cpu_count + 4 for both types of tasks.
            # But we limit it to 32 to avoid consuming surprisingly large resource
            # on many core machine.
            max_workers = min(32, (os.cpu_count() or 1) + 4)
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")

        if initializer is not None and not callable(initializer):
            raise TypeError("initializer must be a callable")

        self._max_workers = max_workers
        self._work_queue = queue.SimpleQueue()
        self._idle_semaphore = threading.Semaphore(0)
        self._threads = set() # 存放worker实例
        self._broken = False
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._thread_name_prefix = (thread_name_prefix or
                                    ("ThreadPoolExecutor-%d" % self._counter()))
        self._initializer = initializer
        self._initargs = initargs

    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock, _global_shutdown_lock:
            if self._broken:
                raise BrokenThreadPool(self._broken)

            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')
            if _shutdown:
                raise RuntimeError('cannot schedule new futures after '
                                   'interpreter shutdown')

            f = _base.Future()
            w = _WorkItem(f, fn, args, kwargs)

            self._work_queue.put(w)
            self._adjust_thread_count()
            return f
    submit.__doc__ = _base.Executor.submit.__doc__

    def _adjust_thread_count(self):
        # if idle threads are available, don't spin new threads
        if self._idle_semaphore.acquire(timeout=0):
            return

        # When the executor gets lost, the weakref callback will wake up
        # the worker threads.
        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = '%s_%d' % (self._thread_name_prefix or self,
                                     num_threads)
            t = threading.Thread(name=thread_name, target=_worker,
                                 args=(weakref.ref(self, weakref_cb),
                                       self._work_queue,
                                       self._initializer,
                                       self._initargs))
            t.start()
            self._threads.add(t)
            _threads_queues[t] = self._work_queue

    def _initializer_failed(self):
        with self._shutdown_lock:
            self._broken = ('A thread initializer failed, the thread pool '
                            'is not usable anymore')
            # Drain work queue and mark pending futures failed
            while True:
                try:
                    work_item = self._work_queue.get_nowait()
                except queue.Empty:
                    break
                if work_item is not None:
                    work_item.future.set_exception(BrokenThreadPool(self._broken))

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_lock:
            self._shutdown = True
            if cancel_futures:
                # Drain all work items from the queue, and then cancel their
                # associated futures.
                while True:
                    try:
                        work_item = self._work_queue.get_nowait()
                    except queue.Empty:
                        break
                    if work_item is not None:
                        work_item.future.cancel()

            # Send a wake-up to prevent threads calling
            # _work_queue.get(block=True) from permanently blocking.
            self._work_queue.put(None)
        if wait:
            for t in self._threads:
                t.join()
    shutdown.__doc__ = _base.Executor.shutdown.__doc__


```
- ThreadPoolExecutor中有几个比较重要的属性:1._max_workers:最大工作线程数 2._work_queue:任务队列.每次用户提交的task都会被push到任务队列里面.3._idle_semaphore,是否有空闲的*worker*，是的话不会再去创建新的*worker*。
- 调用submit后会生成一个*future*,用来存放task的运行成果.然后会生成一个*work_item*并push到*work_queue*里面.
- _adjust_thread_count是调整线程池大小.主要是根据`_idle_semaphore`来判断，如果acquire成功,说明有空闲的*worker*,则不创建.否则创建一个一个新的*worker*

## 总结
总的来说,ThreadPoolExecutor是通过生成对应的数量的*worker*来执行用户提交的task.worker每执行完一个任务后并不会销毁（不同于普通线程）而是去不断从轮询*ThreadPoolExecutor.worker_Queue*队列,知道有新任务到来并执行.从而达到线程复用,避免频繁的线程创建销毁和切换。当然，如果的执行的逻辑周期较长,可能就不适合用线程池来处理(长期霸占一个*worker*).



