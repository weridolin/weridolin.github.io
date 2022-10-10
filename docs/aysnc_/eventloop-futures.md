## 协程函数。
在python中,通过**async**关键字可以定义一个协程函数,每个协程函数必须包含一个**await**语句,表示等待一个I/O事件,由**yield/yield from**的学习可知,await的伪代码相当于**yield from**,此时会把函数挂起,直到下次调用send()方法激活,在次期间程序的执行交换给对应的**event-loop**。
<!-- **async**定义的函数相当于做了一层**CoroWrapper**的封装,源码和注释如下:
```python 
class CoroWrapper:
    # Wrapper for coroutine object in _DEBUG mode.

    def __init__(self, gen, func=None):
        assert inspect.isgenerator(gen) or inspect.iscoroutine(gen), gen
        ### 调用的 async定义的函数的时候（比如asyncio.run(mock_sleep())）,我们会直接传入 method(),
        ### 此时是生成一个生成器
        self.gen = gen
        self.func = func  # Used to unwrap @coroutine decorator
        self._source_traceback = format_helpers.extract_stack(sys._getframe(1))
        self.__name__ = getattr(gen, '__name__', None)
        self.__qualname__ = getattr(gen, '__qualname__', None)

    def __repr__(self):
        coro_repr = _format_coroutine(self)
        if self._source_traceback:
            frame = self._source_traceback[-1]
            coro_repr += f', created at {frame[0]}:{frame[1]}'

        return f'<{self.__class__.__name__} {coro_repr}>'

    def __iter__(self):
        return self

    def __next__(self): # for xx in xxxxx: send(None)并驱动生成器往下运行
        return self.gen.send(None)

    def send(self, value): # 相当于驱动生成器继续往下运行
        return self.gen.send(value)

    def throw(self, type, value=None, traceback=None):
        return self.gen.throw(type, value, traceback) # 生成器抛出异常

    def close(self):
        return self.gen.close() # 关闭生成器

    @property
    def gi_frame(self):
        return self.gen.gi_frame

    @property
    def gi_running(self):
        return self.gen.gi_running

    @property
    def gi_code(self):
        return self.gen.gi_code

    def __await__(self):
        return self

    @property
    def gi_yieldfrom(self):
        return self.gen.gi_yieldfrom

    def __del__(self):
        # Be careful accessing self.gen.frame -- self.gen might not exist.
        gen = getattr(self, 'gen', None)
        frame = getattr(gen, 'gi_frame', None)
        if frame is not None and frame.f_lasti == -1:
            msg = f'{self!r} was never yielded from'
            tb = getattr(self, '_source_traceback', ())
            if tb:
                tb = ''.join(traceback.format_list(tb))
                msg += (f'\nCoroutine object created at '
                        f'(most recent call last, truncated to '
                        f'{constants.DEBUG_STACK_DEPTH} last lines):\n')
                msg += tb.rstrip()
            logger.error(msg)
```
-->
正是利用了生成器能将执行的函数挂起的特性,当遇到函数耗时的I/0操作时,能够直接调用**await**(yield from)将程序的执行权交还给event-loop,event-loop再去对应执行其他的coro函数,避免空等待I/0操作.,而当I/O操作完成时,event-loop又会调用对应的send()方法,驱动其继续执行.

### 一个协程的执行过程(调用asyncio.run运行).

#### 运行前的处理
假设我们定义了一个协程函数**mock_sleep**,然后用**asyncio.run**去运行(协程函数只能用事件循环来驱动运行):       

```python

async def mock_sleep():
    for i in range(10):
        print(">>>> 第{i}次执行")
        await asyncio.sleep(1) # yield from generator

asyncio.run(mock_sleep())
```     
- 1. 对于一个协程/generator等支持异步的对象,asyncio都会把其封装一个**task**(future)对象.**async**方法会初始化一个事件循环,并运行该事件循环,直到该**task**执行完成:  
```python

def run(main, *, debug=None):
    # 如果当前事件循环在运行,则不能通过run方法来启动运行协程
    if events._get_running_loop() is not None:
        raise RuntimeError(
            "asyncio.run() cannot be called from a running event loop")

    if not coroutines.iscoroutine(main): # 执行的函数必须是一个协程
        raise ValueError("a coroutine was expected, got {!r}".format(main))
    loop = events.new_event_loop()
    try:
        events.set_event_loop(loop)
        if debug is not None:
            loop.set_debug(debug)
        ## 启动事件循环,直到协程(main)运行完成
        return loop.run_until_complete(main)
    finally:
        try:
            # 运行完成,清理event-loop中剩余的其他数据
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            events.set_event_loop(None)
            loop.close()

```

- 2. **loop.run_until_complete**是event-loop的一个方法,表示运行coro,直到其运行完成:       
```python

    def run_until_complete(self, future):
        self._check_closed()
        self._check_running()

        new_task = not futures.isfuture(future)
        # 把core封装成一个task（继承自future）对象
        future = tasks.ensure_future(future, loop=self)
            ...
            # _run_until_complete_cb方法:停止事件循环,只要core执行完成,即停止event-loop,所以将其作为回调函数
        future.add_done_callback(_run_until_complete_cb)
        try:
            self.run_forever() # 开始运行事件循环，下面会提到 
        except: 
            if new_task and future.done() and not future.cancelled():
                future.exception()
            raise
        finally:
            future.remove_done_callback(_run_until_complete_cb)
        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')
        # 返回运行的结果
        return future.result()

```


- 3. **tasks.ensure_future(future, loop)**:把协程封装成一个task(future)对象,并注册到对应的event-loop里面:           
```python

def ensure_future(coro_or_future, *, loop=None):

    if coroutines.iscoroutine(coro_or_future):
        if loop is None:
            loop = events.get_event_loop()
        task = loop.create_task(coro_or_future) # 这里是关键,相当把协程函数封装成task对象并注册到 event-loop里面
        if task._source_traceback:
            del task._source_traceback[-1]
        return task
    elif futures.isfuture(coro_or_future):
        if loop is not None and loop is not futures._get_loop(coro_or_future):
            raise ValueError('The future belongs to a different loop than '
                            'the one specified as the loop argument')
        return coro_or_future
    elif inspect.isawaitable(coro_or_future):
        return ensure_future(_wrap_awaitable(coro_or_future), loop=loop)
    else:
        raise TypeError('An asyncio.Future, a coroutine or an awaitable is '
                        'required')


```

总的来说,当定义了一个**async**函数后,函数本身就相当于一个生成器,利用生成器可以挂起的特点,实现当遇到耗时I/O的时候，能够让出执行权，每个**async**定义的函数会被封装成对应的**future(task)**对象.通过event-loop来驱动(调用的task.__step())

#### 开始运行
- 1. 现在开始运行**mock_sleep**,由于在初始化task时,会直接预激活1次，调用一次loop.call_soon.协程会运行到一个yield处返回,即运行到**await asyncio.sleep(1)**,此时返回的是一个future对象.代表的是**asyncio.sleep**的执行结果.
- 2. 因为**mock_sleep**要等到**asyncio.sleep**执行完成才会继续往下执行.所以将**mock_sleep**的唤醒方法**wake**(mock_sleep被封装成一个Task类,wake为Task类中的方法)添加到**asyncio.sleep**（await XX:返回一个future对象）的执行完成回调里面(调用fut.add_done_callback)。
- 3 **asyncio.sleep**执行完,执行对应的回调函数**__wake**,将**mock_sleep**唤醒,**mock_sleep**继续执行。

## eventloop
事件循环是Python异步编程中非常重要的概念,一般每个线程对应着``一个``事件循环,并且控制该线程中所有的协程/异步任务的运行。比如当前线程中有task1,task2,注册到当前线程的eventLoop中.当task1运行遇到I/O操作时，运行控制权会交还给该线程的事件循环*eventLoop*，该线程对应的事件循环就会接着运行*task2*.达到并发的效果.如果运行一个阻塞任务,则该线程下的所有的其他task都不会执行(比如sleep(10000)，除非用asyncio.sleep()).在一个线程定义的coro,不能在另外线程的event-loop中被调用.


#### baseEventloop源码

注释如下

```python
##  asynico.base_envent.py 这里只是抄送了一部分
class BaseEventLoop(events.AbstractEventLoop):

    def __init__(self):
        self._timer_cancelled_count = 0
        self._closed = False
        self._stopping = False
        # 存放待执行的CALLBACK 列表，双向队列,这里的callback被封装成 handle/timerHandle对象
        self._ready = collections.deque()       
        self._scheduled = [] ## 需要延迟执行的tasks。堆的数据结构，是一个优先队列
        self._default_executor = None ## 默认的线程池执行器(可以用来执行同步的代码,即同步代码以异步的方式执行)
        self._internal_fds = 0
        # Identifier of the thread running the event loop, or None if the
        # event loop is not running
        self._thread_id = None # 线程ID
        self._clock_resolution = time.get_clock_info('monotonic').resolution
        self._exception_handler = None
        self.set_debug(coroutines._is_debug_mode())
        # In debug mode, if the execution of a callback or a step of a task
        # exceed this duration in seconds, the slow callback/task is logged.
        self.slow_callback_duration = 0.1
        self._current_handle = None
        self._task_factory = None # 创建任务，默认为tasks.Task()
        self._coroutine_origin_tracking_enabled = False
        self._coroutine_origin_tracking_saved_depth = None

        # A weak set of all asynchronous generators that are
        # being iterated by the loop.
        self._asyncgens = weakref.WeakSet() # 储存注册到该事件循环的所有的 generator,即为所有task
        # Set to True when `loop.shutdown_asyncgens` is called.
        self._asyncgens_shutdown_called = False # 停止所有的generator
        # Set to True when `loop.shutdown_default_executor` is called.
        self._executor_shutdown_called = False # 停止线程池执行器


    def _asyncgen_finalizer_hook(self, agen):
        self._asyncgens.discard(agen)
        if not self.is_closed():
            self.call_soon_threadsafe(self.create_task, agen.aclose())

    def _asyncgen_firstiter_hook(self, agen):
        if self._asyncgens_shutdown_called:
            warnings.warn(
                f"asynchronous generator {agen!r} was scheduled after "
                f"loop.shutdown_asyncgens() call",
                ResourceWarning, source=self)

        self._asyncgens.add(agen)

    async def shutdown_asyncgens(self):
        """
            Shutdown all active asynchronous generators.
            关闭所有的已经注册到该event-loop的所有tasks
        
        """
        self._asyncgens_shutdown_called = True

        if not len(self._asyncgens):
            # If Python version is <3.6 or we don't have any asynchronous
            # generators alive.
            return

        closing_agens = list(self._asyncgens)
        self._asyncgens.clear()

        results = await tasks.gather(
            *[ag.aclose() for ag in closing_agens],
            return_exceptions=True,
            loop=self)

        for result, agen in zip(results, closing_agens):
            if isinstance(result, Exception):
                self.call_exception_handler({
                    'message': f'an error occurred during closing of '
                               f'asynchronous generator {agen!r}',
                    'exception': result,
                    'asyncgen': agen
                })

    async def shutdown_default_executor(self):
        """关闭默认的执行线程池"""
        self._executor_shutdown_called = True
        if self._default_executor is None:
            return
        future = self.create_future()
        thread = threading.Thread(target=self._do_shutdown, args=(future,))
        thread.start()
        try:
            await future
        finally:
            thread.join()

    def _do_shutdown(self, future):
        try:
            self._default_executor.shutdown(wait=True)
            self.call_soon_threadsafe(future.set_result, None)
        except Exception as ex:
            self.call_soon_threadsafe(future.set_exception, ex)

    def _check_running(self):
        if self.is_running():
            raise RuntimeError('This event loop is already running')
        if events._get_running_loop() is not None:
            raise RuntimeError('Cannot run the event loop while another loop is running')

    def run_forever(self):
        """Run until stop() is called."""
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()

        old_agen_hooks = sys.get_asyncgen_hooks()
        ## 设置HOOK. firstiter用于添加到self._asyncgens
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
                               finalizer=self._asyncgen_finalizer_hook)
        try:
            # 设置loop为全局的事件循环,这里时一个进程对应一个事件循环
            events._set_running_loop(self)
            while True:
                # run forever其实就是的运行run once
                self._run_once()
                if self._stopping:
                    break
        finally:
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None) #
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*old_agen_hooks)

    def run_until_complete(self, future):
        """Run until the Future is done.

        If the argument is a coroutine, it is wrapped in a Task.

        WARNING: It would be disastrous to call run_until_complete()
        with the same coroutine twice -- it would wrap it in two
        different Tasks and that can't be good.

        Return the Future's result, or raise its exception.
        """
        self._check_closed()
        self._check_running()

        new_task = not futures.isfuture(future)
        future = tasks.ensure_future(future, loop=self)
        if new_task:
            # An exception is raised if the future didn't complete, so there
            # is no need to log the "destroy pending task" message
            future._log_destroy_pending = False

        future.add_done_callback(_run_until_complete_cb)
        try:
            self.run_forever()
        except:
            if new_task and future.done() and not future.cancelled():
                # The coroutine raised a BaseException. Consume the exception
                # to not log a warning, the caller doesn't have access to the
                # local task.
                future.exception()
            raise
        finally:
            future.remove_done_callback(_run_until_complete_cb)
        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')

        return future.result()


    def call_later(self, delay, callback, *args, context=None):
        """Arrange for a callback to be called at a given time.

        Return a Handle: an opaque object with a cancel() method that
        can be used to cancel the call.

        The delay can be an int or float, expressed in seconds.  It is
        always relative to the current time.

        Each callback will be called exactly once.  If two callbacks
        are scheduled for exactly the same time, it undefined which
        will be called first.

        Any positional arguments after the callback will be passed to
        the callback when it is called.
        """
        timer = self.call_at(self.time() + delay, callback, *args,
                             context=context)
        if timer._source_traceback:
            del timer._source_traceback[-1]
        return timer

    def call_at(self, when, callback, *args, context=None):
        """Like call_later(), but uses an absolute time.

        Absolute time corresponds to the event loop's time() method.
        """
        self._check_closed()
        if self._debug:
            self._check_thread()
            self._check_callback(callback, 'call_at')
        ## 封装成对应的 handle
        timer = events.TimerHandle(when, callback, args, self, context)
        if timer._source_traceback:
            del timer._source_traceback[-1]
        heapq.heappush(self._scheduled, timer) # _scheduled 一个优先队列.最小堆，事件小的在最上面
        timer._scheduled = True
        return timer

    def call_soon(self, callback, *args, context=None):
        """Arrange for a callback to be called as soon as possible.

        This operates as a FIFO queue: callbacks are called in the
        order in which they are registered.  Each callback will be
        called exactly once.

        Any positional arguments after the callback will be passed to
        the callback when it is called.
        """
        self._check_closed()
        if self._debug:
            self._check_thread()
            self._check_callback(callback, 'call_soon')
        handle = self._call_soon(callback, args, context)
        if handle._source_traceback:
            del handle._source_traceback[-1]
        return handle

    def _call_soon(self, callback, args, context):
        ## 立马把callback添加到 _ready 列表，最快可以在下次遍历ready列表就执行
        handle = events.Handle(callback, args, self, context)
        if handle._source_traceback:
            del handle._source_traceback[-1]
        self._ready.append(handle) # ready普通队列,先进先出
        return handle

    def call_soon_threadsafe(self, callback, *args, context=None):
        """Like call_soon(), but thread-safe."""
        self._check_closed()
        if self._debug:
            self._check_callback(callback, 'call_soon_threadsafe')
        handle = self._call_soon(callback, args, context)
        if handle._source_traceback:
            del handle._source_traceback[-1]
        self._write_to_self()
        return handle

    def run_in_executor(self, executor, func, *args):
        self._check_closed()
        if self._debug:
            self._check_callback(func, 'run_in_executor')
        if executor is None:
            executor = self._default_executor
            # Only check when the default executor is being used
            self._check_default_executor()
            if executor is None:
                executor = concurrent.futures.ThreadPoolExecutor(
                    thread_name_prefix='asyncio'
                )
                self._default_executor = executor
        return futures.wrap_future(
            executor.submit(func, *args), loop=self)

    def _add_callback(self, handle):
        """Add a Handle to _scheduled (TimerHandle) or _ready."""
        assert isinstance(handle, events.Handle), 'A Handle is required here'
        if handle._cancelled:
            return
        assert not isinstance(handle, events.TimerHandle)
        self._ready.append(handle)

    def _add_callback_signalsafe(self, handle):
        """Like _add_callback() but called from a signal handler."""
        self._add_callback(handle)
        self._write_to_self()

    def _timer_handle_cancelled(self, handle):
        """Notification that a TimerHandle has been cancelled."""
        if handle._scheduled:
            self._timer_cancelled_count += 1

    def _run_once(self):
        ## 两个队列  self._scheduled是存放延迟执行的任务的队列. 
        ##  self._ready 存放的是即将要执行的队列
        sched_count = len(self._scheduled)

        # _scheduled的长度不是无限的.
        if (sched_count > _MIN_SCHEDULED_TIMER_HANDLES and
            self._timer_cancelled_count / sched_count >
                _MIN_CANCELLED_TIMER_HANDLES_FRACTION):
            new_scheduled = []

            ## 先过滤掉已经被取消的task
            for handle in self._scheduled:
                if handle._cancelled:
                    handle._scheduled = False
                else:
                    new_scheduled.append(handle)

            heapq.heapify(new_scheduled) # 优先队列,按时间排序的最小堆
            self._scheduled = new_scheduled
            self._timer_cancelled_count = 0
        else:
        # 从待执行任务队列中移除所有cancelled状态的任务
            while self._scheduled and self._scheduled[0]._cancelled:
                self._timer_cancelled_count -= 1
                handle = heapq.heappop(self._scheduled)
                handle._scheduled = False

        timeout = None
        ## ready 里面有待处理的callback.表示这次循环有东西要处理，需要马上执行
        if self._ready or self._stopping:
            timeout = 0

        elif self._scheduled: 
            # _scheduled[0]其实就是最早要执行的任务.（优先队列,按执行时间排序）
            when = self._scheduled[0]._when
            timeout = min(max(0, when - self.time()), MAXIMUM_SELECT_TIMEOUT)

        # windows上面是利用select IO模型来驱动的,这个子类实现。基类主要实现回调的处理
        # 如果协程里面有I/O操作,当完成触发事件后,会在这里返回 TODO
        event_list = self._selector.select(timeout)
        self._process_events(event_list)

        # 把self._scheduled中所有到期需要处理的task弹出并添加到 ready队列,并执行
        # 因为 scheduled是一个优先队列,只要找到开始时间不必当前时间大的为止,
        # 后面肯定都是当前时间之后执行的
        end_time = self.time() + self._clock_resolution
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                # 第一个执行时间大于end_time，后面的执行时间肯定都大于end_time
                break
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            # 把
            self._ready.append(handle)

        # 运行ready中的所有任务
        ntodo = len(self._ready)
        for i in range(ntodo):
            ## 处理 _ready中所有完成的任务/callback
            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            if self._debug:
                try:
                    self._current_handle = handle
                    t0 = self.time()
                    handle._run()
                    dt = self.time() - t0
                    if dt >= self.slow_callback_duration:
                        logger.warning('Executing %s took %.3f seconds',
                                    _format_handle(handle), dt)
                finally:
                    self._current_handle = None
            else:
                handle._run()
        handle = None  # Needed to break cycles when an exception occurs.

```

- *BaseEventLoop*中主要有两个比较重要的属性，*scheduled*:主要是记录一些延迟的待执行(非马上执行)的任务(为最小堆堆的数据结构，优先队列，按照执行时间排序).*ready*主要是才存放当前可以执行的任务(不需要延时)。

- *event loop*每次循环都会去做从*scheduled* 找出所有已经需要执行的*task*(既满足执行时间小于当前时间的任务)，添加到*ready*队列中.接着会执行完*ready*中所有待执行的任务. 

- 所有的有异步任务都会通过*asyncgen_firstiter_hook*方法添加到*asyncgens*属性里面

- 往event-loop中添加任务,当任务不需要延时执行时,调用**loop.call_soon**,把函数添加到loop._ready队列,loop会在下次循环执行,当任务需要延迟执行时,往**loop._shceduled**优先队列种添加该任务.

- event-loop添加的任务类型都被封装成为 Handler/TimeHandler封装后的对象，对于Task封装了协程后的对象来说，此时执行的是task.__step()方法，即相当于 Handler.run --> task.__step()



## Handle和TimeHandle
handle和timeHandle是对coro的进一步封装.是event-loop的最终执行对象.对于即可执行的coro.会被封装成对应的handle,而对于要延迟执行的coro,会被封装成对应的TimeHandler对象.         
Handle和TimeHandler的源码和注释如下:    
```python


```





#### 添加事件监听
- call_later(self, delay, callback, *args, context=None):   
需要延迟执行的对应的callback回调.delay为延迟多少秒执行.会被添加到*loop._scheduled*队列.*asyncio.sleep*的实现方式就是调用了call_later. 

```python

async def sleep(delay, result=None, *, loop=None):
    """Coroutine that completes after a given time (in seconds)."""
    if delay <= 0:
        await __sleep0()
        return result

    if loop is None:
        loop = events.get_running_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, ""and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)
    future = loop.create_future()
    # 延迟执行，添加到 loop._scheduled 队列
    h = loop.call_later(delay,
                        futures._set_result_unless_cancelled,
                        future, result)
    # print(">>> ready",loop._ready,">>> scheduled",loop._scheduled)
    try:
        # 等到执行完成,
        return await future
    finally:
        h.cancel()
```

- call_soon:
马上执行，调用*call_soon*会把回调添加到*loop._ready*队列，会在下次遍历*_ready*时马上去执行.



##### loop.run_forever()

```python
    def __init__(self, coro, *, loop=None, name=None):
        super().__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[-1]
        if not coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        if name is None:
            self._name = f'Task-{_task_name_counter()}'
        else:
            self._name = str(name)

        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        self._context = contextvars.copy_context()

        self._loop.call_soon(self.__step, context=self._context)
        _register_task(self)

    ...
    def run_forever(self):
        """Run until stop() is called."""
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()

        old_agen_hooks = sys.get_asyncgen_hooks()
        ## 设置HOOK. firstiter用于添加到self._asyncgens
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
                               finalizer=self._asyncgen_finalizer_hook)
        try:
            # 设置loop为全局的事件循环,这里时一个进程对应一个事件循环
            events._set_running_loop(self)
            while True:
                self._run_once()
                if self._stopping:
                    break
        finally:
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None)
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*old_agen_hooks)
    ...

    def _run_once(self):
        """Run one full iteration of the event loop.

        This calls all currently ready callbacks, polls for I/O,
        schedules the resulting callbacks, and finally schedules
        'call_later' callbacks.
        """

        ## 两个队列  self._scheduled是存放延迟执行的任务的队列. self._ready 存放的是即将要执行的队列
        sched_count = len(self._scheduled)
        if (sched_count > _MIN_SCHEDULED_TIMER_HANDLES and
            self._timer_cancelled_count / sched_count >
                _MIN_CANCELLED_TIMER_HANDLES_FRACTION):
            # Remove delayed calls that were cancelled if their number
            # is too high
            new_scheduled = []
            for handle in self._scheduled:
                if handle._cancelled:
                    handle._scheduled = False
                else:
                    new_scheduled.append(handle)

            heapq.heapify(new_scheduled)
            self._scheduled = new_scheduled
            self._timer_cancelled_count = 0
        else:
            # 检测第一个任务是否为取消，是的话直接移除
            # Remove delayed calls that were cancelled from head of queue.
            while self._scheduled and self._scheduled[0]._cancelled:
                self._timer_cancelled_count -= 1
                handle = heapq.heappop(self._scheduled)
                handle._scheduled = False

        timeout = None
        ## ready 里面有待处理的callback.表示这次循环有东西要处理
        if self._ready or self._stopping:
            timeout = 0
        elif self._scheduled: # 这次循环没有待处理的callback,则检测延迟处理堆是否有到时间需要处理的任务
            # Compute the desired timeout.
            when = self._scheduled[0]._when
            timeout = min(max(0, when - self.time()), MAXIMUM_SELECT_TIMEOUT)



        # windows 上面是利用select IO模型来驱动的,这个子类实现。基类主要实现回调的处理
        event_list = self._selector.select(timeout)
        self._process_events(event_list)


        # 把self._scheduled中所有到期需要处理的task弹出并添加到 ready队列，并执行
        # Handle 'later' callbacks that are ready.
        end_time = self.time() + self._clock_resolution
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                break
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            self._ready.append(handle)

        # This is the only place where callbacks are actually *called*.
        # All other places just add them to ready.
        # Note: We run all currently scheduled callbacks, but not any
        # callbacks scheduled by callbacks run this time around --
        # they will be run the next time (after another I/O poll).
        # Use an idiom that is thread-safe without using locks.
        ntodo = len(self._ready)
        for i in range(ntodo):
            ## 处理 _ready中所有完成的任务/callback
            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            if self._debug:
                try:
                    self._current_handle = handle
                    t0 = self.time()
                    handle._run()
                    dt = self.time() - t0
                    if dt >= self.slow_callback_duration:
                        logger.warning('Executing %s took %.3f seconds',
                                    _format_handle(handle), dt)
                finally:
                    self._current_handle = None
            else:
                handle._run()
        handle = None  # Needed to break cycles when an exception occurs.
```
run_forever其实就是不断去运行*run_once*，先检测*scheduled*中需要执行的任务添加到*ready*.接着selectIO模型对异步任务进行调用(`event_list = self._selector.select(timeout)self._process_events(event_list)`)，最后执行*ready*中待执行的callback.

#### selectEventLoop
*selectEventLoop*是基于SELECT IO模型的事件循环,主要用来*selector高级库*.继承于*BaseEventLoop*.直接看源码注释
```python
## asyncio.selector_event.py
class BaseSelectorEventLoop(base_events.BaseEventLoop):
    """Selector event loop.

    See events.EventLoop for API specification.

    ## READERS --> INPUTS |  WRITERS --> OUTPUTS
    """

    def __init__(self, selector=None):
        super().__init__()

        if selector is None:
            selector = selectors.DefaultSelector()
        logger.debug('Using selector: %s', selector.__class__.__name__)
        self._selector = selector
        self._make_self_pipe()
        self._transports = weakref.WeakValueDictionary()

    ...
    def _add_reader(self, fd, callback, *args):
        self._check_closed()
        handle = events.Handle(callback, args, self, None)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_READ,
                                    (handle, None))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_READ,
                                  (handle, writer))
            if reader is not None:
                reader.cancel()
        return handle


    def _add_writer(self, fd, callback, *args):
        self._check_closed()
        handle = events.Handle(callback, args, self, None) #loop每个callback都会封装成handle
        try:
            key = self._selector.get_key(fd) # selector是否已经监听该I/O？
        except KeyError:
            self._selector.register(fd, selectors.EVENT_WRITE,
                                    (None, handle)) # selector不存在该IO监听，注册添加
        else:
            # selector已经存在监听，修改状态
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_WRITE,
                                  (reader, handle))
            if writer is not None:# 把原来该I/O对应的写状态的回调取消掉，读的状态的回调保留
                writer.cancel()
        return handle


    def _process_events(self, event_list):
        for key, mask in event_list:
            fileobj, (reader, writer) = key.fileobj, key.data
            if mask & selectors.EVENT_READ and reader is not None:
                if reader._cancelled:
                    self._remove_reader(fileobj)
                else:
                    self._add_callback(reader)
            if mask & selectors.EVENT_WRITE and writer is not None:
                if writer._cancelled:
                    self._remove_writer(fileobj)
                else:
                    self._add_callback(writer)
    
```
主要看*add_reader*,*add_writer*,*process_events*3个函数.由*baseEventLoop*的代码可以知道,loop每次循环的时候,会运行`event_list = self._selector.select(timeout)self._process_events(event_list)`.对于*selectEventLoop*来说。就是调用select.Select,得到可读/写的文件IO事件列表，如果取消,则从selector中注销，否则接着调用*add_callback*,把该任务的回调添加到loop的*ready*里面去执行.
- *add_reader*,*add_writer*,就是注册监听一个文件I/O的状态,loop会监听对应的事件并进行过相应的回调处理。
- 注意I/O操作是在内核中执行的，用户态这边只是负责接收I/O的状态并执行回调.
- 总的来说,大致的逻辑就是当遇到一个I/O任务时,先往*eventloop*注册一个事件回调.当内核IO完成时,触发回调.*eventloop*再完成回调函数的逻辑。


#### IOCPEventLoop
#### TODO

## asyncio.futures
*future*在python异步编程中可以理解为一个异步任务的执行结果,所有的异步任务都是一个继承了*future*的对象，其提供了*result*,*add_done_callback*等方法提供调用.
-  result():返回 Future 的结果。如果 Future 状态为 完成 ，并由 set_result() 方法设置一个结果（task的返回值），则返回这个结果。如果 Future 状态为完成 ，并由set_exception()方法设置一个异常(task运行异常)，那么这个方法会引发异常。如果Future已取消，方法会引发一个 CancelledError 异常。如果 Future 的结果还不可用，此方法会引发一个InvalidStateError异常。
- 与*concurrent.futures.Future*类不同,asyncio.Future为可等待的对象*await future*

## await future
等待future执行完成.即*self._state*的状态为*finish*.  

```python
## future __await__

def __await__(self):
    if not self.done():
        self._asyncio_future_blocking = True
        yield self  # This tells Task to wait for completion.下次还是调用的 self.__await__
    if not self.done():
        raise RuntimeError("await wasn't used with future")
    return self.result()  # May raise too.

```
*await*其实就是相当于*yield from*.即在迭代器停止前会不断去迭代。具体可参考*yield from*的[伪代码逻辑](/docs/aysnc_/python-yield.md).*asyncio.sleep*就是一个典型的例子。

```python

async def sleep(delay, result=None, *, loop=None):
    """Coroutine that completes after a given time (in seconds)."""
    if delay <= 0:
        await __sleep0()
        return result

    if loop is None:
        loop = events.get_running_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)

    future = loop.create_future()
    h = loop.call_later(delay,
                        # 通过_set_result_unless_cancelled，设置future state来结束
                        futures._set_result_unless_cancelled, 
                        future, result)
    # print(">>> ready",loop._ready,">>> scheduled",loop._scheduled)
    try:
        return await future
    finally:
        h.cancel()

def _set_result_unless_cancelled(fut, result):
    """Helper setting the result only if the future was not cancelled."""
    if fut.cancelled():
        return
    fut.set_result(result)

# class Future
def set_result(self, result):
    """Mark the future done and set its result.

    If the future is already done when this method is called, raises
    InvalidStateError.
    """
    if self._state != _PENDING:
        raise exceptions.InvalidStateError(f'{self._state}: {self!r}')
    self._result = result
    self._state = _FINISHED
    self.__schedule_callbacks()

```
- 通过调用*call_later*,将*set_result_unless_cancelled*设置为一个延时callback添加到*loop._scheduled*里面.在*set_result_unless_cancelled*执行前，*future*的状态始终不为*finish*.*await future*(相当于*yield from future*)也不会结束。当达到延时时间后，*set_result_unless_cancelled*被loop添加到*ready*并执行,此时*await future*执行结束（参考future.__await__）



## task
task是对*协程*多加了一层封装.继承了*asyncio.futures*,通过方法*__step()*方法驱动*协程*的运行,直接看源码

```python 
class Task:
    
    def __init__(self, coro, *, loop=None, name=None):
        super().__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[-1]
        if not coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        if name is None:
            self._name = f'Task-{_task_name_counter()}'
        else:
            self._name = str(name)

        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        self._context = contextvars.copy_context()

        ## 初始化时添加到 eventloop的 _ready队列
        self._loop.call_soon(self.__step, context=self._context)
        _register_task(self)
    
    ......

    def __step(self, exc=None):
        ## call soon :在下次时间循环的时候执行
        ## callback：set result / exception 的时候再去执行
        if self.done():
            raise exceptions.InvalidStateError(
                f'_step(): already done: {self!r}, {exc!r}')
        if self._must_cancel:
            if not isinstance(exc, exceptions.CancelledError):
                exc = self._make_cancelled_error()
            self._must_cancel = False
        coro = self._coro
        self._fut_waiter = None

        _enter_task(self._loop, self) # 把CORE注册到到全局变量
        # Call either coro.throw(exc) or coro.send(None).
        try:
            ## 开始驱动协程的运行
            if exc is None:
                # We use the `send` method directly, because coroutines
                # don't have `__iter__` and `__next__` methods.
                result = coro.send(None) # 启动core
            else:
                result = coro.throw(exc) # 有异常直接抛出异常
        except StopIteration as exc:
            ## 异步任务停止执行. 1.提前被取消 2.运行完成,return了值
            if self._must_cancel:
                # Task is cancelled right before coro stops.
                self._must_cancel = False
                super().cancel(msg=self._cancel_message) #
            else:
                super().set_result(exc.value) ## yield return 值会引发
        except exceptions.CancelledError as exc:
            # Save the original exception so we can chain it later.
            self._cancelled_exc = exc #
            super().cancel()  # I.e., Future.cancel(self).
        except (KeyboardInterrupt, SystemExit) as exc:
            super().set_exception(exc)
            raise
        except BaseException as exc:
            super().set_exception(exc)
        else:
            blocking = getattr(result, '_asyncio_future_blocking', None)
            if blocking is not None:
                # Yielded Future must come from Future.__iter__().
                if futures._get_loop(result) is not self._loop:
                    new_exc = RuntimeError(
                        f'Task {self!r} got Future '
                        f'{result!r} attached to a different loop')
                    self._loop.call_soon(
                        self.__step, new_exc, context=self._context) # 
                elif blocking:
                    if result is self:
                        new_exc = RuntimeError(
                            f'Task cannot await on itself: {self!r}')
                        self._loop.call_soon(
                            self.__step, new_exc, context=self._context)
                    else:
                        result._asyncio_future_blocking = False
                        result.add_done_callback( ## callback是在set result/exception时再去执行的
                            self.__wakeup, context=self._context)
                        self._fut_waiter = result
                        if self._must_cancel:
                            if self._fut_waiter.cancel(
                                    msg=self._cancel_message):
                                self._must_cancel = False
                else:
                    new_exc = RuntimeError(
                        f'yield was used instead of yield from '
                        f'in task {self!r} with {result!r}')
                    self._loop.call_soon(
                        self.__step, new_exc, context=self._context)

            elif result is None:
                # Bare yield relinquishes control for one event loop iteration.
                self._loop.call_soon(self.__step, context=self._context)
            elif inspect.isgenerator(result):
                # Yielding a generator is just wrong.
                new_exc = RuntimeError(
                    f'yield was used instead of yield from for '
                    f'generator in task {self!r} with {result!r}')
                self._loop.call_soon(
                    self.__step, new_exc, context=self._context)
            else:
                # Yielding something else is an error.
                new_exc = RuntimeError(f'Task got bad yield: {result!r}')
                self._loop.call_soon(
                    self.__step, new_exc, context=self._context)
        finally:
            _leave_task(self._loop, self)
            self = None  # Needed to break cycles when an exception occurs.

    def __wakeup(self, future):
        try:
            future.result()
        except BaseException as exc:
            # This may also be a cancellation.
            self.__step(exc)
        else:
            # Don't pass the value of `future.result()` explicitly,
            # as `Future.__iter__` and `Future.__await__` don't need it.
            # If we call `_step(value, None)` instead of `_step()`,
            # Python eval loop would use `.send(value)` method call,
            # instead of `__next__()`, which is slower for futures
            # that return non-generator iterators from their `__iter__`.
            self.__step()
        self = None  # Needed to break cycles when an exception occurs.


```
- 初始化task时,将*task.__step*添加到绑定的*eventLoop*的*ready*队列上(调用call_soon)
- *eventLoop*开始运行,每次都会去运行*ready*中的*task*，即运行*task.__step*
- *task.__step*开始运行，运行到I/O操作(该I/O操作必须为异步,否则不会让出控制权)开始让出控制权.判断是否运行完成/异常.是的话把回调函数再添加到*_ready*队列里面下次运行.如果返回的result为None,说明异步函数还没有运行完成(函数运行完成会触发*stopIteration*).直接把*__step*添加到*ready*队列运行.


## loop.run_in_executor     
当*loop*运行一个阻塞的任务时.整个事件循环会阻塞，及当前的线程也会阻塞,对应的其他task也不会执行。要是想把一个阻塞的任务/或者同步代码编程异步,可以用*loop.run_in_executor*,以线程方式去运行，当前对应的事件循环也不会进入阻塞状态.源码如下:
```python

    ## baseEventLoop
    ...


    def _check_callback(self, callback, method):
        if (coroutines.iscoroutine(callback) or
                coroutines.iscoroutinefunction(callback)):
            raise TypeError(
                f"coroutines cannot be used with {method}()") # 协程不能调用该方法
        if not callable(callback): # 必须为函数，
            raise TypeError(
                f'a callable object was expected by {method}(), '
                f'got {callback!r}')

    def run_in_executor(self, executor, func, *args):
        self._check_closed()
        if self._debug:
            self._check_callback(func, 'run_in_executor')
        if executor is None:
            executor = self._default_executor
            # Only check when the default executor is being used
            self._check_default_executor()
            if executor is None:
                # 默认调用线程池去运行
                executor = concurrent.futures.ThreadPoolExecutor(
                    thread_name_prefix='asyncio'
                )
                self._default_executor = executor
        return futures.wrap_future(
            executor.submit(func, *args), loop=self)
    
    # 把 concurrent.futures.Future 封装成 awaitable的 asynico.future
    def wrap_future(future, *, loop=None):
        """Wrap concurrent.futures.Future object."""
        if isfuture(future):
            return future
        assert isinstance(future, concurrent.futures.Future), \
            f'concurrent.futures.Future is expected, got {future!r}'
        if loop is None:
            loop = events.get_event_loop()
        new_future = loop.create_future()
        _chain_future(future, new_future)
        return new_future

    def _chain_future(source, destination):
        """Chain two futures so that when one completes, so does the other.

        The result (or exception) of source will be copied to destination.
        If destination is cancelled, source gets cancelled too.
        Compatible with both asyncio.Future and concurrent.futures.Future.
        """
        if not isfuture(source) and not isinstance(source,
                                                concurrent.futures.Future):
            raise TypeError('A future is required for source argument')
        if not isfuture(destination) and not isinstance(destination,
                                                        concurrent.futures.Future):
            raise TypeError('A future is required for destination argument')
        source_loop = _get_loop(source) if isfuture(source) else None
        dest_loop = _get_loop(destination) if isfuture(destination) else None

        def _set_state(future, other):
            ## 把线程运行完成的future.result赋值给 asynico.future实例*new_future*
            if isfuture(future):
                _copy_future_state(other, future)
            else:
                _set_concurrent_future_state(future, other)

        def _call_check_cancel(destination):
            ## 检测线程运行返回的结果是不是cancel
            if destination.cancelled():
                if source_loop is None or source_loop is dest_loop:
                    source.cancel()
                else:
                    source_loop.call_soon_threadsafe(source.cancel)

        def _call_set_state(source):
            if (destination.cancelled() and
                    dest_loop is not None and dest_loop.is_closed()):
                return
            if dest_loop is None or dest_loop is source_loop:
                _set_state(destination, source)
            else:
                dest_loop.call_soon_threadsafe(_set_state, destination, source)

        destination.add_done_callback(_call_check_cancel)
        source.add_done_callback(_call_set_state) # 把线程池的函数执行完添加一个回调，把运行完成的结果赋值给asynico.future实例*new_future*
```
- 因为线程里面运行的返回的是 *concurrent.futures.Future*实例,这是一个非*awaitable*对象,必须把其转换成一个可*awaitable*的*asynico.future*对象.这里采用的方式先创建一个*asynico.future*实例*new_future*,在把*concurrent.futures.Future*的运行结果赋给*new_future*。


