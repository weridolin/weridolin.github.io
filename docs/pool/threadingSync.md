### threading.Lock
threading.lock是最原生的一个线程同步的方法,调用*acquire*时获取锁.调用*release*时释放锁.同个线程调用*acquire*后，必须调用*release*才能再次去*acquire*。
#### threading.RLock
threading.RLock是对原生的lock的改进。主要是支持同个线程同时对同个*lock*调用*acquire*.同时释放的话也要调用多次(调用了多少次*acquire*就要调用多少次*release*).
```python
class _RLock:

    def __init__(self):
        self._block = _allocate_lock()
        self._owner = None
        self._count = 0

    def __repr__(self):
        owner = self._owner
        try:
            owner = _active[owner].name
        except KeyError:
            pass
        return "<%s %s.%s object owner=%r count=%d at %s>" % (
            "locked" if self._block.locked() else "unlocked",
            self.__class__.__module__,
            self.__class__.__qualname__,
            owner,
            self._count,
            hex(id(self))
        )

    def _at_fork_reinit(self):
        self._block._at_fork_reinit()
        self._owner = None
        self._count = 0

    def acquire(self, blocking=True, timeout=-1):
        """Acquire a lock, blocking or non-blocking.

        When invoked without arguments: if this thread already owns the lock,
        increment the recursion level by one, and return immediately. Otherwise,
        if another thread owns the lock, block until the lock is unlocked. Once
        the lock is unlocked (not owned by any thread), then grab ownership, set
        the recursion level to one, and return. If more than one thread is
        blocked waiting until the lock is unlocked, only one at a time will be
        able to grab ownership of the lock. There is no return value in this
        case.

        When invoked with the blocking argument set to true, do the same thing
        as when called without arguments, and return true.

        When invoked with the blocking argument set to false, do not block. If a
        call without an argument would block, return false immediately;
        otherwise, do the same thing as when called without arguments, and
        return true.

        When invoked with the floating-point timeout argument set to a positive
        value, block for at most the number of seconds specified by timeout
        and as long as the lock cannot be acquired.  Return true if the lock has
        been acquired, false if the timeout has elapsed.

        """
        me = get_ident()
        if self._owner == me:
            ### 同个线程调用了acquire,用count记录了同个线程调用了多少次
            self._count += 1
            return 1
        ### 当前LOCKER的拥有者不是该线程而是其他线程
        rc = self._block.acquire(blocking, timeout)
        if rc:
            self._owner = me
            self._count = 1
        return rc

    __enter__ = acquire

    def release(self):
        """Release a lock, decrementing the recursion level.

        If after the decrement it is zero, reset the lock to unlocked (not owned
        by any thread), and if any other threads are blocked waiting for the
        lock to become unlocked, allow exactly one of them to proceed. If after
        the decrement the recursion level is still nonzero, the lock remains
        locked and owned by the calling thread.

        Only call this method when the calling thread owns the lock. A
        RuntimeError is raised if this method is called when the lock is
        unlocked.

        There is no return value.

        """
        if self._owner != get_ident():
            ## 只能调用了 acquire的线程去 release.不能跨线程去release
            raise RuntimeError("cannot release un-acquired lock")
        self._count = count = self._count - 1
        if not count:
            self._owner = None
            self._block.release()

    def __exit__(self, t, v, tb):
        self.release()


    def _is_owned(self):
        return self._owner == get_ident()

```
- RLock在内部通过count变量来记录同个线程调用的次数,只要是同个线程，可以多次调用*acquire*。但释放时也要多次调用*release*
- Rlock不是线程安全的，即只能在同个线程去*acquire*和*release*
- Lock可以跨线程去*acquire*和*release*


### threading.Condition
threading.Condition是用来做线程同步的一种方式，其支持条件触发的方式去对多个线程做同步。比如线程B在满足条件A后才激活，就可以用condition来做同步:⬇️        
```python
class Condition:
    """Class that implements a condition variable.

    A condition variable allows one or more threads to wait until they are
    notified by another thread.

    If the lock argument is given and not None, it must be a Lock or RLock
    object, and it is used as the underlying lock. Otherwise, a new RLock object
    is created and used as the underlying lock.

    """

    def __init__(self, lock=None):
        if lock is None:
            lock = RLock()
        self._lock = lock
        # Export the lock's acquire() and release() methods
        self.acquire = lock.acquire
        self.release = lock.release
        # If the lock defines _release_save() and/or _acquire_restore(),
        # these override the default implementations (which just call
        # release() and acquire() on the lock).  Ditto for _is_owned().
        try:
            self._release_save = lock._release_save
        except AttributeError:
            pass
        try:
            self._acquire_restore = lock._acquire_restore
        except AttributeError:
            pass
        try:
            self._is_owned = lock._is_owned
        except AttributeError:
            pass
        self._waiters = _deque()

        ...

    def _is_owned(self):
        ## 是否获得锁，notify之前必须先获取锁
        # Return True if lock is owned by current_thread.
        # This method is called only if _lock doesn't have _is_owned().
        if self._lock.acquire(False):
            self._lock.release()
            return False
        else:
            return True

    def wait(self, timeout=None):
        """Wait until notified or until a timeout occurs.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method releases the underlying lock, and then blocks until it is
        awakened by a notify() or notify_all() call for the same condition
        variable in another thread, or until the optional timeout occurs. Once
        awakened or timed out, it re-acquires the lock and returns.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        When the underlying lock is an RLock, it is not released using its
        release() method, since this may not actually unlock the lock when it
        was acquired multiple times recursively. Instead, an internal interface
        of the RLock class is used, which really unlocks it even when it has
        been recursively acquired several times. Another internal interface is
        then used to restore the recursion level when the lock is reacquired.

        """
        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        waiter = _allocate_lock()
        waiter.acquire()
        self._waiters.append(waiter)
        saved_state = self._release_save()
        gotit = False
        try:    # restore state no matter what (e.g., KeyboardInterrupt)
            if timeout is None:
                waiter.acquire()
                gotit = True
            else:
                if timeout > 0:
                    gotit = waiter.acquire(True, timeout)
                else:
                    gotit = waiter.acquire(False)
            return gotit
        finally:
            ## 重新获取锁，因为进入wait之前要获取锁，进入wait之后释放锁，离开wait之后要恢复重新获取锁
            self._acquire_restore(saved_state)
            if not gotit:
                try:
                    self._waiters.remove(waiter)
                except ValueError:
                    pass

    def wait_for(self, predicate, timeout=None):
        """Wait until a condition evaluates to True.

        predicate should be a callable which result will be interpreted as a
        boolean value.  A timeout may be provided giving the maximum time to
        wait.

        """
        ## 根据 predicate()的执行结果来判断，当predicate()返回False时，则会无线等待下去，直到返回true.
        ## 判断是否为true之前还必须返回调用下 notify 跳出 wait。

        endtime = None
        waittime = timeout
        result = predicate()
        while not result:
            if waittime is not None:
                if endtime is None:
                    endtime = _time() + waittime
                else:
                    waittime = endtime - _time()
                    if waittime <= 0:
                        break
            self.wait(waittime)  # 这里重新wait，此时是在_waiters队列尾部的位置
            result = predicate()
        return result

    def notify(self, n=1):
        """Wake up one or more threads waiting on this condition, if any.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method wakes up at most n of the threads waiting for the condition
        variable; it is a no-op if no threads are waiting.

        """
        if not self._is_owned():
            raise RuntimeError("cannot notify on un-acquired lock")
        all_waiters = self._waiters
        waiters_to_notify = _deque(_islice(all_waiters, n))
        if not waiters_to_notify:
            return
        for waiter in waiters_to_notify:
            # 每个调用了condition.wait()的方法的thread都会获得一个内部锁，这个锁会被添加到condition的_waiters属性里面
            # 当调用了notify方法时，就会去获取_waiters里面等待的锁，然后一一释放。_waiter实际上是个双向队列，也是先进先出
            waiter.release()
            try:
                all_waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        """Wake up all threads waiting on this condition.

        If the calling thread has not acquired the lock when this method
        is called, a RuntimeError is raised.

        """
        self.notify(len(self._waiters))

    notifyAll = notify_all

```
- condition在其内部维护了一个_waiters队列，用来存所有进入wait状态的线程.当线程调用了*con.wait*后.con内部会分配一把而外的锁并push到队列里面去.只有调用notify后.才会一次去释放_waiters队列中的锁，对应去唤醒_wait状态的线程。
- condition本身自带了一个lock.通过上下文去调用时，实际上是获得一把互斥锁
- 调用wait()时.必须先获得内部的互斥锁
- 例子：    

```python

from threading import Condition,Thread
import threading
import time

def child(condition:Condition):
    with condition:
        print("get condition",threading.current_thread(),"beign to wait")
        condition.wait() # 调用wait之后，con会给改线程分配一把锁lock,线程会进入lock.acquire()的阻塞状态
        # print(condition._waiters) 
        print("get condition",threading.current_thread(),"awake ")
        time.sleep(2)

if __name__ == "__main__":
    con = threading.Condition()
    for i in range(3):
        t = Thread(target=child,args=(con,))
        t.start()
    time.sleep(2)
    # con.notify_all()
    with con:
        con.notify(1) # 释放condition._waiters里面的第一把锁，激活该锁对应的线程


### 打印输出为:
# get condition <Thread(Thread-1, started 21372)> beign to wait
# get condition <Thread(Thread-2, started 4704)> beign to wait
# get condition <Thread(Thread-3, started 20724)> beign to wait
# get condition <Thread(Thread-1, started 21372)> awak
```

- condition.wait_for()支持传入可调用对象，只有当改可调用对象返回true时，才会进入激活状态，否则将一直处于wait状态.例子:⬇️

```python
from threading import Condition,Thread
import threading
import time
from functools import partial

def child(condition:Condition,index):
    with condition:
        print("get condition",threading.current_thread(),"beign to wait")
        condition.wait_for(predicate=partial(wait_for_condition,index))
        # print(condition._waiters)
        time.sleep(2)
        print("get condition",threading.current_thread(),"awake ")
        time.sleep(2)

def wait_for_condition(index):
    print(">>> check index",index)
    if index>=2:
        return False
    else:
        return True


if __name__ == "__main__":
    con = threading.Condition()
    for i in range(4):
        t = Thread(target=child,args=(con,i))
        t.start()
    time.sleep(2)
    with con:
        con.notify_all()
    time.sleep(3)
    with con:
        con.notify_all()

### 输出为
get condition <Thread(Thread-1, started 21580)> beign to wait
>>> check index 0 
get condition <Thread(Thread-1, started 21580)> awake   ## 满足 condition
get condition <Thread(Thread-2, started 20788)> beign to wait
>>> check index 1
get condition <Thread(Thread-2, started 20788)> awake  ## 满足 condition
get condition <Thread(Thread-3, started 1032)> beign to wait  
>>> check index 2                                     ## 不满足 condition
get condition <Thread(Thread-4, started 8312)> beign to wait
>>> check index 3                                    ## 不满足 condition

    ### 第一次调用 con.notify_all().首先是thread-2,不满足wait_for_condition()返回True的条件，所以重新
    ### 调用con.wait().此时原来thread-2对应的lock在con.__waiters列表中从头部编程尾部。
    ### 接着是 thread-3。逻辑跟thread-2一致
>>> check index 2
>>> check index 3


    ### 第二次调用 con.notify_all().首先是thread-2,不满足wait_for_condition()返回True的条件，所以重新
    ### 调用con.wait().此时原来thread-2对应的lock在con.__waiters列表中从头部编程尾部。
    ### 接着是 thread-3。逻辑跟thread-2一致
>>> check index 2
>>> check index 3


```

### threading.Semaphore
Semaphore信号量也是用来做线程同步的一种方式.先直接看源码:⬇️

```python
class Semaphore:
    """This class implements semaphore objects.

    Semaphores manage a counter representing the number of release() calls minus
    the number of acquire() calls, plus an initial value. The acquire() method
    blocks if necessary until it can return without making the counter
    negative. If not given, value defaults to 1.

    """

    # After Tim Peters' semaphore class, but not quite the same (no maximum)

    ## 默认信号量为1，即只允许一个线程去去执行。
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self._cond = Condition(Lock())
        self._value = value

    def acquire(self, blocking=True, timeout=None):
        """Acquire a semaphore, decrementing the internal counter by one.

        When invoked without arguments: if the internal counter is larger than
        zero on entry, decrement it by one and return immediately. If it is zero
        on entry, block, waiting until some other thread has called release() to
        make it larger than zero. This is done with proper interlocking so that
        if multiple acquire() calls are blocked, release() will wake exactly one
        of them up. The implementation may pick one at random, so the order in
        which blocked threads are awakened should not be relied on. There is no
        return value in this case.

        When invoked with blocking set to true, do the same thing as when called
        without arguments, and return true.

        When invoked with blocking set to false, do not block. If a call without
        an argument would block, return false immediately; otherwise, do the
        same thing as when called without arguments, and return true.

        When invoked with a timeout other than None, it will block for at
        most timeout seconds.  If acquire does not complete successfully in
        that interval, return false.  Return true otherwise.

        """
        if not blocking and timeout is not None:
            raise ValueError("can't specify timeout for non-blocking acquire")
        rc = False
        endtime = None
        with self._cond:
            while self._value == 0:
                if not blocking:
                    break
                if timeout is not None:
                    if endtime is None:
                        endtime = _time() + timeout
                    else:
                        timeout = endtime - _time()
                        if timeout <= 0:
                            break
                ## value为0,获取不到信号量，直接进入wait状态
                self._cond.wait(timeout)
            else:
                # 否则获得执行权,可执行的信号量减一
                self._value -= 1
                rc = True
        return rc

    __enter__ = acquire

    def release(self, n=1):
        """Release a semaphore, incrementing the internal counter by one or more.

        When the counter is zero on entry and another thread is waiting for it
        to become larger than zero again, wake up that thread.

        """
        if n < 1:
            raise ValueError('n must be one or more')
        with self._cond:
            self._value += n
            for i in range(n):
                self._cond.notify()

    def __exit__(self, t, v, tb):
        self.release()


```

- Semaphore 实际上也是在内部维护了一个condition对象。并通过内置的_value属性来控制同时允许运行的线程的最大数量。
- 调用Semaphore.acquire时,先判断当前信号量的值是否为0，不为0的话直接获得执行权，为0的话调用内部的con.wait()获得内部锁.进入等待状态。
- 调用Semaphore.release,释放信号量，修改value值，同时将因为获取不到信号量而进入con.wait的线程唤醒。



### 关于多个线程同时竞争Lock/condition/semaphore的问题
- 如果是多个线程同时竞争同一个*Lock/condition/semaphore*,如果有con/sem释放时,则遵循先来先到原则.先进入_waiters队列的先获取到释放的锁。比如按照时间顺序先后A,B,C分别等待同个*con/sem*。如果此时满足条件，则A会优先获得该释放的锁.如果是调用了*con.wait_for(predict)*去等待,而*predict()*返回False的情况,则此时A会再次去调用con.wait().添加到*con._waiters*的队列的尾部.当下次再有锁释放时,则B会优先获得执行权。
- 如果要在一个线程*acquire*.在另外一个线程*release*。只能用原生*lock*(*condition*初始化可以自定义lock类型),不能用*Rlock*。
- semaphore内部用的原生的Lock，也是线程安全的

### 关于threading中使用sleep()记录  
在平时接触的工作中,发现有时需要对**thread**sleep一下在继续运行.而在sleep过程中需要能够做到中途wake并结束sleep.这里总结了以下2种方法:
- 1. 把sleep拆解成多个小时长的sleep*次数.在循环中间进行其他逻辑处理
- 2. 利用threading.Event()实例中的wait方法,threading.event().wait()是一个阻塞等待的过程，中途如果有其他线程set了该event,则立马中断等待,实际案例可以参考线程池中的[as_completed函数]('./_processPool.md')

```python

import threading,time


class SleepThread(threading.Thread):
    
    exit_flag = False

    def run(self) -> None:
        ## 把sleep拆成多个小间隔的sleep
        for _ in range(1000):
            # sleep过程中响应对应的逻辑操作
            if self.exit_flag:
                print("exit")
                break
            time.sleep(0.1)
        return super().run()

class SleepThread(threading.Thread):
    
    exit_flag = threading.Event()

    def run(self) -> None:
        ## 把sleep拆成多个小间隔的sleep
        self.exit_flag.wait(100)
        print("exit")
        return super().run()


if __name__ =="__main__":
    t = SleepThread()
    t.start()
    time.sleep(2)

    # 以下方式都可以马上让thread中断sleep继续执行
    
    t.exit_flag=True # 自定义退出标记
    t.exit_flag.set() # 利用 threading.Event()的set来退出


    t.join()
```

### 从子线程中退出整个程序   
线程的退出/异常一般情况下不会影响到主线程的运行.但在平时接触到的需求中，有时候需要在子线程收到某个消息后，退出整个程序,比如子线程起个服务,收到特定消息后退出程序,这里总结了以下使用过方法:
- 1. 子/主线程之间通过一个Queue去通信.
- 2. 利用**threading.main_thread()**,主线程对象，再调用对应的退出逻辑.
- 3. 初始化子线程时，指定parent.直接调用parent中的退出逻辑.     

```python 



```
