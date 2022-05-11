#### 基于asynico模块的一个小尝试
"""

    # 基于 asyncio.base_event_loop的一个延迟队列

    ## todo1:同一时间点多个任务执行
    ## todo2:run block add task

"""
import asyncio
from typing import Callable
from functools import partial
from asyncio.events import TimerHandle
from threading import Thread

# class C

class DelayQueueBase(object):

    def __init__(self,max_length,*,loop=None) -> None:
        if not loop:
            self.__loop = asyncio.get_event_loop()
        else:
            self.__loop = loop

        self.max_length = max_length
        self.__task = dict()
        self._block = False
        self._thread = None
        
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
    
    def push(self,task,name,delay=None,*callback_args,**callback_kwargs):
        if len(self.__task.keys())>=self.max_length:
            raise RuntimeError("is attach task queue max length")
        if name in self.__task.keys():
            raise TypeError(f"task:{name} is already in scheduled")
        if not isinstance(task,Callable):
            raise TypeError("task is not callable")
        else:
            _callback = self._wrap_callback(callback=task,name=name,**callback_kwargs)
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
    
    def _wrap_callback(self,callback,name,**callback_kwargs):
        _callback = partial(callback,**callback_kwargs)
        def _wrap(*callback_args):
            _callback(*callback_args)
            if name in self.__task.keys():
                self.__task.pop(name)
        return _wrap


    def pop(self,name):
        if name not in self.__task.keys():
            raise TypeError(f"task:{name} not register!")
        else:
            handle = self.__task.get(name)
            if isinstance(handle,TimerHandle):
                if not handle._scheduled:
                    raise RuntimeError(f"task:{name} is not in queue!")
                if  handle.cancelled:
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
    time.sleep(1)


if __name__ =="__main__":
    d_queue = DelayQueueBase(max_length=10)
    d_queue.run_noblock()
    for i in range(2):
        d_queue.push(task,name=f"task-{i}",delay=i+3,index=i+3)

    while 1:
        time.sleep(1)
        if len(d_queue.task.keys()) == 0:
            d_queue.stop()
            break

