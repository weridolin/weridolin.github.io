### 基于*asyncio.baseEventLoop*的延迟队列实现

```python

#### 基于asynico模块的一个小尝试
"""

    # 基于 asyncio.base_event_loop的一个延迟队列

"""
import asyncio
from typing import Callable
from functools import partial
from asyncio.events import TimerHandle
from threading import Thread
from asyncio.base_events import BaseEventLoop,MAXIMUM_SELECT_TIMEOUT,_MIN_SCHEDULED_TIMER_HANDLES,_MIN_CANCELLED_TIMER_HANDLES_FRACTION,heapq
from asyncio.windows_events import SelectorEventLoop
from asyncio.futures import _FINISHED,_CANCELLED

class DelayQueueBaseEventLoop(SelectorEventLoop):
    
    def _run_once(self):
        """Run one full iteration of the event loop.

        This calls all currently ready callbacks, polls for I/O,
        schedules the resulting callbacks, and finally schedules
        'call_later' callbacks.

        # 把run改为线程池去运行
        """

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
            # Remove delayed calls that were cancelled from head of queue.
            while self._scheduled and self._scheduled[0]._cancelled:
                self._timer_cancelled_count -= 1
                handle = heapq.heappop(self._scheduled)
                handle._scheduled = False

        if self._ready or self._stopping:
            timeout = 0
        elif self._scheduled:
            # Compute the desired timeout.
            when = self._scheduled[0]._when
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
            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            # self.run_in_executor(None,handle._run)
            handle._run()
        handle = None  # Needed to break cycles when an exception occurs.


class DelayQueueBase(object):

    def __init__(self,max_length,*,loop=None) -> None:
        if not loop:
            # self.__loop = asyncio.get_event_loop()
            self.__loop = DelayQueueBaseEventLoop()
            asyncio.set_event_loop(self.__loop)
        else:
            self.__loop = loop

        self.max_length = max_length
        self.__task = dict()
        self._block = False
        self._thread = None
        # self._pool = 

    def _run_block(self):
        self._block = True
        if self.__loop:
            self.__loop.run_forever()
        else:
            raise RuntimeError("loop is not running")

    def run_noblock(self):
        self._block = False
        self._thread = Thread(target=self._run_block,daemon=True)
        self._thread.start()

    def stop(self):
        if self.__loop:
            self.__loop.stop()
            print(self.__loop._scheduled,self.__loop._ready)
    
    def push(self,task,name,delay=None,*callback_args,**callback_kwargs):
        if len(self.__task.keys())>=self.max_length:
            raise RuntimeError("is attach task queue max length")
        if name in self.__task.keys():
            raise TypeError(f"task:{name} is already in scheduled")
        if not isinstance(task,Callable):
            raise TypeError("task is not callable")
        else:
            _callback = self._wrap_callback(callback=task,name=name,loop=self.__loop,**callback_kwargs)
            handle = self._add_to_loop(delay=delay,callback=_callback,*callback_args)
            self.__task.update({name:handle})
        
    def _add_to_loop(self,delay,callback,*callback_args):
        if delay and delay<=0:
            return self.__loop.call_soon_threadsafe(
                callback,*callback_args
            )
        else:
            return self.__loop.call_later(
                delay=delay,callback=callback,*callback_args
            )
    
    def _wrap_callback(self,callback,name,loop,**callback_kwargs):
        _callback = partial(callback,**callback_kwargs)
        def _wrap(*callback_args):
            future = loop.run_in_executor(None,_callback,*callback_args)
            future.add_done_callback(partial(self._remove_task,name))
            print(self.__loop._scheduled,self.__loop._ready)
            # _callback(*callback_args)
            # if name in self.__task.keys():
            #     self.__task.pop(name)
        return _wrap

    def _remove_task(self,name,future):
        # print(self.__loop._scheduled,self.__loop._ready)
        if future._state in [_CANCELLED,_FINISHED]:

            if name in self.__task.keys():
                self.__task.pop(name)

    def pop(self,name):
        if name not in self.__task.keys():
            raise TypeError(f"task:{name} not register!")
        else:
            handle = self.__task.get(name)
            if isinstance(handle,TimerHandle):
                if not handle._scheduled:
                    raise RuntimeError(f"task:{name} is not in queue!")
                if handle.cancelled:
                    raise RuntimeError(f"task:{name} is already cancel!")
                handle.cancel()
            else:
                ## 只有延迟任务才能取消
                raise RuntimeError(f"task:{name} is already finish")

    @property
    def task(self):
        return self.__task

import time
def task(index):
    print(f"I am a delay {index+1} task")
    time.sleep(index)
    print(f">>>  {index}")


if __name__ =="__main__":
    d_queue = DelayQueueBase(max_length=10)
    d_queue.run_noblock()
    for i in range(3):
        d_queue.push(task,name=f"task-{i}",delay=4,index=i+3)

    while 1:
        time.sleep(1)
        if len(d_queue.task.keys()) == 0:
            d_queue.stop()
            break



```