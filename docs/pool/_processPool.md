## process pool
跟线程池一样.进程池也是优化了进程的复用,避免进程的频繁创建和销毁.线程中具体分为3大件.
- 1.ProcessPoolExecutor:进程池执行器.跟*ProcessPoolExecutor*类似.
- 2.LocalWorkerThread: 负责task的调度和运行结果的调度反馈,作用类似一个中间调度和沟通的桥梁.
- 3.ProcessWorker:工作进程,实际工作的进程.


### ProcessPoolExecutor
直接贴源码:

```python

class ProcessPoolExecutor(_base.Executor):
    def __init__(self, max_workers=None, mp_context=None,
                initializer=None, initargs=()):
        """Initializes a new ProcessPoolExecutor instance.

        Args:
            max_workers: The maximum number of processes that can be used to
                execute the given calls. If None or not given then as many
                worker processes will be created as the machine has processors.
            mp_context: A multiprocessing context to launch the workers. This
                object should provide SimpleQueue, Queue and Process.
            initializer: A callable used to initialize worker processes.
            initargs: A tuple of arguments to pass to the initializer.
        """
        _check_system_limits()

        if max_workers is None:
            self._max_workers = os.cpu_count() or 1
            if sys.platform == 'win32':
                self._max_workers = min(_MAX_WINDOWS_WORKERS,
                                        self._max_workers)
        else:               
            if max_workers <= 0:
                raise ValueError("max_workers must be greater than 0")
            elif (sys.platform == 'win32' and
                max_workers > _MAX_WINDOWS_WORKERS):
                raise ValueError(
                    f"max_workers must be <= {_MAX_WINDOWS_WORKERS}")

            self._max_workers = max_workers

        if mp_context is None:
            mp_context = mp.get_context()
        self._mp_context = mp_context

        if initializer is not None and not callable(initializer):
            raise TypeError("initializer must be a callable")
        self._initializer = initializer
        self._initargs = initargs

        # Management thread
        self._executor_manager_thread = None
 
        # Map of pids to processes
        self._processes = {}

        # Shutdown is a two-step process.
        self._shutdown_thread = False
        self._shutdown_lock = threading.Lock()
        self._idle_worker_semaphore = threading.Semaphore(0)
        self._broken = False
        self._queue_count = 0 # submit的任务总数
        self._pending_work_items = {} # 待执行的任务
        self._cancel_pending_futures = False

        # _ThreadWakeup is a communication channel used to interrupt the wait
        # of the main loop of executor_manager_thread from another thread (e.g.
        # when calling executor.submit or executor.shutdown). We do not use the
        # _result_queue to send wakeup signals to the executor_manager_thread
        # as it could result in a deadlock if a worker process dies with the
        # _result_queue write lock still acquired.
        #
        # _shutdown_lock must be locked to access _ThreadWakeup.
        self._executor_manager_thread_wakeup = _ThreadWakeup()

        # Create communication channels for the executor
        # Make the call queue slightly larger than the number of processes to
        # prevent the worker processes from idling. But don't make it too big
        # because futures in the call queue cannot be cancelled.
        queue_size = self._max_workers + EXTRA_QUEUED_CALLS
        self._call_queue = _SafeQueue(
            max_size=queue_size, ctx=self._mp_context,
            pending_work_items=self._pending_work_items,
            shutdown_lock=self._shutdown_lock,
            thread_wakeup=self._executor_manager_thread_wakeup)
        # Killed worker processes can produce spurious "broken pipe"
        # tracebacks in the queue's own worker thread. But we detect killed
        # processes anyway, so silence the tracebacks.
        self._call_queue._ignore_epipe = True
        self._result_queue = mp_context.SimpleQueue()
        self._work_ids = queue.Queue()

    def _start_executor_manager_thread(self):
        if self._executor_manager_thread is None:
            # Start the processes so that their sentinels are known.
            self._executor_manager_thread = _ExecutorManagerThread(self) # 该EXecutor与所有process的通信？
            self._executor_manager_thread.start()
            _threads_wakeups[self._executor_manager_thread] = \
                self._executor_manager_thread_wakeup # 

    def _adjust_process_count(self):
        # if there's an idle process, we don't need to spawn a new one.
        ## 如果当前有空余进程未执行。则不在创建进程
        if self._idle_worker_semaphore.acquire(blocking=False):
            return 
        # 已经运行的进程总数
        process_count = len(self._processes) 
        if process_count < self._max_workers: 
            p = self._mp_context.Process( # 
                target=_process_worker,
                args=(self._call_queue,
                    self._result_queue,
                    self._initializer,
                    self._initargs))
            p.start()
            self._processes[p.pid] = p

    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock:
            if self._broken:
                raise BrokenProcessPool(self._broken)
            if self._shutdown_thread:
                raise RuntimeError('cannot schedule new futures after shutdown')
            if _global_shutdown:
                raise RuntimeError('cannot schedule new futures after '
                                'interpreter shutdown')

            f = _base.Future()
            w = _WorkItem(f, fn, args, kwargs)
            ## executor本身缓冲字典
            self._pending_work_items[self._queue_count] = w 
            self._work_ids.put(self._queue_count)  #     
            self._queue_count += 1
            # Wake up queue management thread
            ## management thread中的wait_result_broken_or_wakeup是一个阻塞的过程，如果没有
            ## 结果返回的话.所以submit时必须wakeup，才会触发management thread add_call_item_to_queue中的方法。把task从 _pending_work_items 添加到 call queue 
            self._executor_manager_thread_wakeup.wakeup()

            self._adjust_process_count()
            self._start_executor_manager_thread()
            return f
    submit.__doc__ = _base.Executor.submit.__doc__

    def map(self, fn, *iterables, timeout=None, chunksize=1):
        """Returns an iterator equivalent to map(fn, iter).

        Args:
            fn: A callable that will take as many arguments as there are
                passed iterables.
            timeout: The maximum number of seconds to wait. If None, then there
                is no limit on the wait time.
            chunksize: If greater than one, the iterables will be chopped into
                chunks of size chunksize and submitted to the process pool.
                If set to one, the items in the list will be sent one at a time.

        Returns:
            An iterator equivalent to: map(func, *iterables) but the calls may
            be evaluated out-of-order.

        Raises:
            TimeoutError: If the entire result iterator could not be generated
                before the given timeout.
            Exception: If fn(*args) raises for any values.
        """
        if chunksize < 1:
            raise ValueError("chunksize must be >= 1.")

        results = super().map(partial(_process_chunk, fn),
                              _get_chunks(*iterables, chunksize=chunksize),
                              timeout=timeout)
        return _chain_from_iterable_of_lists(results)

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_lock:
            self._cancel_pending_futures = cancel_futures
            self._shutdown_thread = True
            if self._executor_manager_thread_wakeup is not None:
                # Wake up queue management thread
                self._executor_manager_thread_wakeup.wakeup()

        if self._executor_manager_thread is not None and wait:
            self._executor_manager_thread.join()
        # To reduce the risk of opening too many files, remove references to
        # objects that use file descriptors.
        self._executor_manager_thread = None
        self._call_queue = None
        if self._result_queue is not None and wait:
            self._result_queue.close()
        self._result_queue = None
        self._processes = None
        self._executor_manager_thread_wakeup = None

    shutdown.__doc__ = _base.Executor.shutdown.__doc__


```

- 具体的作用跟线程池executor一样,显示创建一个task. push到工作队列中.如果当前有空间进程.则不会去创建的新的工作进程.而当前如果没有工作进程且已经创建的工作进程没有达到上限。则会去创建一个新的worker
- ProcessPoolExecutor有几个比较重要的属性:1._queue_count:可以理解为当前任务的id 2._pending_work_items:待执行的任务({_queue_count:_WorkItem}),submit的时候是直接添加任务到_pending_work_items. 3._call_queue:存放即将被process worker消费的任务 4._result_queue:存放执行结果的队列. 5._work_ids:每个task对应的id.即为_queue_count
- 和线程池不同，进程池submit时会去创建一个_executor_manager_thread.这个线程时负责*executor*和所有的*worker*之间的交互。
- ProcessPoolExecutor中三个队列. 1:_call_queue:存放待执行task的队列,该队列中的task状态不能更改 2._result_queue。存放结果的队列  3._work_ids每个task对应的ID队列。


### ExecutorManagerThread
ExecutorManagerThread 负责executor和所有process worker之间的交互,直接看源码⬇️:

```python
class _ExecutorManagerThread(threading.Thread):
    """Manages the communication between this process and the worker processes.

    The manager is run in a local thread.

    Args:
        executor: A reference to the ProcessPoolExecutor that owns
            this thread. A weakref will be own by the manager as well as
            references to internal objects used to introspect the state of
            the executor.
    """

    def __init__(self, executor):
        # Store references to necessary internals of the executor.

        # A _ThreadWakeup to allow waking up the queue_manager_thread from the
        # main Thread and avoid deadlocks caused by permanently locked queues.
        self.thread_wakeup = executor._executor_manager_thread_wakeup
        self.shutdown_lock = executor._shutdown_lock

        # A weakref.ref to the ProcessPoolExecutor that owns this thread. Used
        # to determine if the ProcessPoolExecutor has been garbage collected
        # and that the manager can exit.
        # When the executor gets garbage collected, the weakref callback
        # will wake up the queue management thread so that it can terminate
        # if there is no pending work item.
        def weakref_cb(_,
                       thread_wakeup=self.thread_wakeup,
                       shutdown_lock=self.shutdown_lock):
            mp.util.debug('Executor collected: triggering callback for'
                          ' QueueManager wakeup')
            with shutdown_lock:
                thread_wakeup.wakeup()

        self.executor_reference = weakref.ref(executor, weakref_cb)
 
        ## 所有已经创建process worker
        self.processes = executor._processes

        # A ctx.Queue that will be filled with _CallItems derived from
        # _WorkItems for processing by the process workers.
        ## 等待被process worker处理的task,不能取消
        self.call_queue = executor._call_queue

        # A ctx.SimpleQueue of _ResultItems generated by the process workers.
        ## 储存task的处理结果
        self.result_queue = executor._result_queue

        # A queue.Queue of work ids e.g. Queue([5, 6, ...]).
        self.work_ids_queue = executor._work_ids

        # A dict mapping work ids to _WorkItems e.g.
        #     {5: <_WorkItem...>, 6: <_WorkItem...>, ...}
        self.pending_work_items = executor._pending_work_items

        super().__init__()

    def run(self):
        # Main loop for the executor manager thread.

        while True:
            ## 运行call queue里面所有的task
            self.add_call_item_to_queue()

            result_item, is_broken, cause = self.wait_result_broken_or_wakeup()

            if is_broken:
                self.terminate_broken(cause)
                return
            if result_item is not None:
                self.process_result_item(result_item)
                # Delete reference to result_item to avoid keeping references
                # while waiting on new results.
                del result_item

                # attempt to increment idle process count
                executor = self.executor_reference()
                if executor is not None:
                    executor._idle_worker_semaphore.release()
                del executor

            if self.is_shutting_down():
                self.flag_executor_shutting_down()

                # Since no new work items can be added, it is safe to shutdown
                # this thread if there are no pending work items.
                if not self.pending_work_items:
                    self.join_executor_internals()
                    return

    def add_call_item_to_queue(self):
        # Fills call_queue with _WorkItems from pending_work_items.
        # This function never blocks.

        ## 从等待队列pending_work_items中获取一个item.并添加到call_queue
        while True:
            if self.call_queue.full():
                return
            try:
                # 获取task对应的id
                work_id = self.work_ids_queue.get(block=False)
            except queue.Empty:
                return
            else:
                work_item = self.pending_work_items[work_id]
                # 判断是否可运行或者取消
                if work_item.future.set_running_or_notify_cancel():
                    # 可运行的话，把任务添加到 call_queue 
                    self.call_queue.put(_CallItem(work_id,
                                                work_item.fn,
                                                work_item.args,
                                                work_item.kwargs),
                                        block=True)
                else:
                    # cancel的话直接取消
                    del self.pending_work_items[work_id]
                    continue

    def wait_result_broken_or_wakeup(self):
        # Wait for a result to be ready in the result_queue while checking
        # that all worker processes are still running, or for a wake up
        # signal send. The wake up signals come either from new tasks being
        # submitted, from the executor being shutdown/gc-ed, or from the
        # shutdown of the python interpreter.

        ## 创建一个reader对象
        result_reader = self.result_queue._reader
        assert not self.thread_wakeup._closed
        wakeup_reader = self.thread_wakeup._reader

        # wakeup_reader是为方便能实时中断wait过程(只要调用thread_wakeup.wakeup即可),因为
        # wait是一个阻塞的过程
        readers = [result_reader, wakeup_reader]
        worker_sentinels = [p.sentinel for p in self.processes.values()]
        ready = mp.connection.wait(readers + worker_sentinels)

        cause = None
        is_broken = True
        result_item = None

        ## result queue 有新的result产生
        if result_reader in ready:
            try:
                result_item = result_reader.recv()
                is_broken = False
            except BaseException as e:
                cause = traceback.format_exception(type(e), e, e.__traceback__)

        elif wakeup_reader in ready:
            is_broken = False

        with self.shutdown_lock:
            self.thread_wakeup.clear()

        return result_item, is_broken, cause

    def process_result_item(self, result_item):
        # Process the received a result_item. This can be either the PID of a
        # worker that exited gracefully or a _ResultItem


        ### 终止 worker process  executor shutdown的时候会会往queue push None
        if isinstance(result_item, int):
            # Clean shutdown of a worker using its PID
            # (avoids marking the executor broken)
            assert self.is_shutting_down() 
            p = self.processes.pop(result_item)
            p.join()
            if not self.processes:
                self.join_executor_internals()
                return 
        else:
            ## 否则把result设置会future
            # Received a _ResultItem so mark the future as completed.
            work_item = self.pending_work_items.pop(result_item.work_id, None)
            # work_item can be None if another process terminated (see above)
            if work_item is not None:
                if result_item.exception:
                    work_item.future.set_exception(result_item.exception)
                else:
                    work_item.future.set_result(result_item.result)

    def is_shutting_down(self):
        # Check whether we should start shutting down the executor.
        executor = self.executor_reference()
        # No more work items can be added if:
        #   - The interpreter is shutting down OR
        #   - The executor that owns this worker has been collected OR
        #   - The executor that owns this worker has been shutdown.
        return (_global_shutdown or executor is None
                or executor._shutdown_thread)

    def terminate_broken(self, cause):
        # Terminate the executor because it is in a broken state. The cause
        # argument can be used to display more information on the error that
        # lead the executor into becoming broken.

        # Mark the process pool broken so that submits fail right now.
        executor = self.executor_reference()
        if executor is not None:
            executor._broken = ('A child process terminated '
                                'abruptly, the process pool is not '
                                'usable anymore')
            executor._shutdown_thread = True
            executor = None

        # All pending tasks are to be marked failed with the following
        # BrokenProcessPool error
        bpe = BrokenProcessPool("A process in the process pool was "
                                "terminated abruptly while the future was "
                                "running or pending.")
        if cause is not None:
            bpe.__cause__ = _RemoteTraceback(
                f"\n'''\n{''.join(cause)}'''")

        # Mark pending tasks as failed.
        for work_id, work_item in self.pending_work_items.items():
            work_item.future.set_exception(bpe)
            # Delete references to object. See issue16284
            del work_item
        self.pending_work_items.clear()

        # Terminate remaining workers forcibly: the queues or their
        # locks may be in a dirty state and block forever.
        for p in self.processes.values():
            p.terminate()

        # clean up resources
        self.join_executor_internals()

    def flag_executor_shutting_down(self):
        # Flag the executor as shutting down and cancel remaining tasks if
        # requested as early as possible if it is not gc-ed yet.
        executor = self.executor_reference()
        if executor is not None:
            executor._shutdown_thread = True
            # Cancel pending work items if requested.
            if executor._cancel_pending_futures:
                # 把还未运行的task从pending_work_items中去除
                # Cancel all pending futures and update pending_work_items
                # to only have futures that are currently running.
                new_pending_work_items = {}
                for work_id, work_item in self.pending_work_items.items():
                    if not work_item.future.cancel():
                        new_pending_work_items[work_id] = work_item
                self.pending_work_items = new_pending_work_items
                # Drain work_ids_queue since we no longer need to
                # add items to the call queue.
                while True:
                    try:
                        self.work_ids_queue.get_nowait()
                    except queue.Empty:
                        break
                # Make sure we do this only once to not waste time looping
                # on running processes over and over.
                executor._cancel_pending_futures = False

    def shutdown_workers(self):
        ### 停止所有的worker.通过向call_queue发送None
        n_children_to_stop = self.get_n_children_alive()
        n_sentinels_sent = 0
        # Send the right number of sentinels, to make sure all children are
        # properly terminated.
        while (n_sentinels_sent < n_children_to_stop
                and self.get_n_children_alive() > 0):
            for i in range(n_children_to_stop - n_sentinels_sent):
                try:
                    self.call_queue.put_nowait(None)
                    n_sentinels_sent += 1
                except queue.Full:
                    break

    def join_executor_internals(self):
        self.shutdown_workers()
        # Release the queue's resources as soon as possible.
        self.call_queue.close()
        self.call_queue.join_thread()
        with self.shutdown_lock:
            self.thread_wakeup.close()
        # If .join() is not called on the created processes then
        # some ctx.Queue methods may deadlock on Mac OS X.
        for p in self.processes.values():
            p.join()

    def get_n_children_alive(self):
        # This is an upper bound on the number of children alive.
        return sum(p.is_alive() for p in self.processes.values())


```
- 每个processPoolExecutor都有一个对应的ExecutorManagerThread。用来管理所有的process worker和executor之间的交互。ExecutorManagerThread会不断去从pending_work_items去读取task中的任务push到call queue给worker消费。
- ExecutorManagerThread中的run会阻塞在wait_result_broken_or_wakeup().知道worker有结果返回或者调用了thread_wakeup.wake up.因为ExecutorManagerThread监听的不只是result_queue中的读事件，还有thread_wakeup中pipe的读事件，类似于select模型。


### processPool worker
processPool worker是进程池实际的工作进程。还是直接看源码:⬇️

```python
def _process_worker(call_queue, result_queue, initializer, initargs):
    """Evaluates calls from call_queue and places the results in result_queue.
    This worker is run in a separate process.
    Args:
        call_queue: A ctx.Queue of _CallItems that will be read and
            evaluated by the worker.
        result_queue: A ctx.Queue of _ResultItems that will written
            to by the worker.
        initializer: A callable initializer, or None
        initargs: A tuple of args for the initializer
    """
    ## 创建前执行的函数
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical('Exception in initializer:', exc_info=True)
            # The parent will notice that the process stopped and
            # mark the pool broken
            return
    while True:
        call_item = call_queue.get(block=True)
        if call_item is None:
            # Wake up queue management thread
            result_queue.put(os.getpid()) # 把该process worker的process id 推到result queue里面
            return
        try:
            r = call_item.fn(*call_item.args, **call_item.kwargs) # 实际运行的函数
        except BaseException as e:
            exc = _ExceptionWithTraceback(e, e.__traceback__)
            _sendback_result(result_queue, call_item.work_id, exception=exc) # 把结果( _ResultItem )推送到 result_queue
        else:
            _sendback_result(result_queue, call_item.work_id, result=r)
            del r

        # Liberate the resource as soon as possible, to avoid holding onto
        # open files or shared memory that is not needed anymore
        del call_item

```
- worker负责从call_queue中获取task并执行.这个步骤跟线程池的worker一致
- 当从call queue中获取到的task为None时(executor调用shutdown会发None).直接把worker的进程ID推到result queue里面。ExecutorManagerThread会去判断并执行终止该process worker的逻辑.


### executor.result_queue
进程池里面所有工作进程*worker*和主进程主要是通过*result_queue*来实现，*result_queue*是一个*SimpleQueue*对象，其实是对一个命名管道(NamedPipe)的封装。我们先看下*SimpleQueue*的源码：⬇️    
```python
class SimpleQueue(object):
    ### PUT _writer 写入  GET _reader 接收

    def __init__(self, *, ctx):
        self._reader, self._writer = connection.Pipe(duplex=False)
        self._rlock = ctx.Lock()
        self._poll = self._reader.poll
        if sys.platform == 'win32':
            self._wlock = None
        else:
            self._wlock = ctx.Lock()

    def close(self):
        self._reader.close()
        self._writer.close()

    def empty(self):
        return not self._poll()

    def __getstate__(self):
        context.assert_spawning(self)
        return (self._reader, self._writer, self._rlock, self._wlock)

    def __setstate__(self, state):
        (self._reader, self._writer, self._rlock, self._wlock) = state
        self._poll = self._reader.poll

    def get(self):
        with self._rlock:
            res = self._reader.recv_bytes()
        # unserialize the data after having released the lock
        return _ForkingPickler.loads(res)

    def put(self, obj):
        ## 写入时先序列化，再写入
        # serialize the data before acquiring the lock
        obj = _ForkingPickler.dumps(obj)
        if self._wlock is None:
            # writes to a message oriented win32 pipe are atomic
            self._writer.send_bytes(obj)
        else:
            with self._wlock:
                self._writer.send_bytes(obj)

```
- 从*simple queue*的源码可以看出,*simple queue*其实就是对PIPE的封装，并且只能从writer端写入.从reader读出，实现类似队列的效果

接下来在看下*connection。PiPe*的代码

```python

def Pipe(duplex=True):
    '''
    Returns pair of connection objects at either end of a pipe
    '''
    address = arbitrary_address('AF_PIPE')
    if duplex:
        ## 双工的，服务端/客户端都可以双向通信
        openmode = _winapi.PIPE_ACCESS_DUPLEX
        access = _winapi.GENERIC_READ | _winapi.GENERIC_WRITE
        obsize, ibsize = BUFSIZE, BUFSIZE
    else:
        ## 单向的,只能从客户端流向服务端。
        openmode = _winapi.PIPE_ACCESS_INBOUND
        access = _winapi.GENERIC_WRITE
        obsize, ibsize = 0, BUFSIZE

    ## 创建一个命名管道，但是实际上未打开？
    h1 = _winapi.CreateNamedPipe(
        address, ## 管道的文件地址
        ## 管道打开方式
        openmode | _winapi.FILE_FLAG_OVERLAPPED |_winapi.FILE_FLAG_FIRST_PIPE_INSTANCE,
        ## 管道模式
        #### 
        _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE |_winapi.PIPE_WAIT,
        ## 管道最大实例数
        1, 
        ## 管道输出缓冲区大小，0为默认
        obsize, 
        ## 管道输入缓冲区大小，0为默认
        ibsize, 
        ## 管道默认等待超时时间
        _winapi.NMPWAIT_WAIT_FOREVER,
        # default security descriptor: the handle cannot be inherited
        _winapi.NULL
        )
    
    ## 创建一个客户端，连接到路径为address的刚刚建立的管道连接，这里返回的还是句柄,
    ## 可以理解为创建一个句柄
    h2 = _winapi.CreateFile(
        ## 文件地址
        address, 

        ## 读写权限
        # 0	我们不希望从设备读取数据或向设备写入数据。如果只想改变设备的配置（比如只是修改文件的时间戳），那么可以传0
        # GENERIC_READ	允许对设备进行只读访问
        # GENERIC_WRITE	允许对设备进行只写访问。
        # GENERIC_READ|GENERIC_WRITE	允许对设备进行读写操作.
        access, 

        ## 共享权限
        # 0	要求独占对设备的访问。如果设备已经打开，CreateFile调用会失败。
        # 如果我们成功地打开了设备，那么后续的CreateFile调用会失败
        # FILE_SHARE_READ	如果有其他内核对象要使用该设备，我们要求它们不得修改设备的数据。
        # 如果设备已经以写入方式或独占方式打开，那么我们的CreateFile调用会失败。
        # 如果我们成功地打开了设备，那么后续的使用了GENERIC_WRITE访问标志的CreateFile调用会失败
        # FILE_SHARE_WRITE	如果有其他内核对象要使用该设备，我们要求它们不得读取设备的数据。
        # 如果设备已经以读取方式或独占方式打开，那么我们的CreateFile调用会失败。
        # 如果我们成功地打开了设备，那么后续的使用了GENERIC_READ访问标志的CreateFile调用会失败
        # FILE_SHARE_READ|FILE_SHARE_WRITE	如果有其他内核对象要使用该设备，
        # 我们不关心它们会从设备读取数据还是会向设备写入数据。如果设备已经以独占方式打开，
        # 那么我们的CreateFile调用会失败。如果我们成功地打开了设备，
        # 那么后续的要求独占读取访问、独占写入访问或独占读写访问的CreateFile调用会失败
        # FILE_SHARE_DELETE	当对文件进行操作的时候，我们不关心文件是否被逻辑删除或是被移动。
        # 在Windows内部，系统会先将文件标记为待删除，然后当该文件所有已打开的句柄都被关闭的时候，
        # 再将其真正的删除
        0, 
        ## 安全级别，一般传NULL即可
        _winapi.NULL,

        ## 创建模式
        # CREATE_NEW	告诉CreateFile创建一个新文件，如果同名文件已经存在，那么CreateFile会调用失败
        # CREATE_ALWAYS	告诉CreateFile无论同名文件存在与否都创建一个新文件。
        # 如果同名文件已经存在，那么CreateFile会覆盖原来的文件
        # OPEN_EXISTING	告诉CreateFile打开一个已有的文件或设备，如果文件或设备不存在，
        # 那么CreateFile会调用失败
        # OPEN_ALWAYS	告诉CreateFile打开一个已有的文件，如果文件存在，
        # 那么CreateFile会直接打开文件，如果文件不存在，那么CreateFile会创建一个新文件
        # TRUNCATE_EXISTING	告诉CreateFile打开一个已有的文件并将文件的大小截断为0字节，
        # 如果文件不存在，那么CreateFile会调用失败
        _winapi.OPEN_EXISTING,

        ## 通信标记，FILE_FLAG_OVERLAPPED 以异步的方式访问设别
        _winapi.FILE_FLAG_OVERLAPPED, 

        # 既可以是标识一个打开的文件的句柄，也可以是NULL
        _winapi.NULL
        )

    _winapi.SetNamedPipeHandleState(
        h2, _winapi.PIPE_READMODE_MESSAGE, None, None
        )

    ## 命名管道h1等待客户端的连接
    overlapped = _winapi.ConnectNamedPipe(h1, overlapped=True)
    _, err = overlapped.GetOverlappedResult(True) ###这个调用过程有点类似Select?
    assert err == 0 ## 已经链接。进入等待数据状态

    ### 连接的同一个pipe
    ### 如果duplex为false.所以pipe mode为PIPE_ACCESS_INBOUND。
    ### 从客户端(连接者)到服务端(创建者).h1(创建者)只能读.h2只能写,
    ### 即PIPE的数据流向为从 连接者--->创建者
    c1 = PipeConnection(h1, writable=duplex)
    c2 = PipeConnection(h2, readable=duplex)

    return c1, c2

```

- 关于管道相关的，可以参考[PiPe](./Pipe.md).总的来说。*simple pipe*就是创建一个命名管道PIPE.然后从作为参数传递给个worker.各个worker把结果通过PIPE中的writer写入到PIPE中,主进程中间管理线程(_ExecutorManagerThread)再调用PIPE中的reader把结果从PIPE中读取出来