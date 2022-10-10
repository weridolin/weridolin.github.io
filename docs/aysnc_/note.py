
# from inspect import getgeneratorstate
from asyncio import subprocess
from concurrent.futures import ProcessPoolExecutor
# class StopException(Exception):pass
import logging
# def count():
#     total,num = 0,1
#     while True:
#         try:
#             new = yield 
#             if new!="stop":
#                 total+=new
#                 num+=1
#             else:
#                 break
#         except StopException:
#             print("throw stop exception")
#             # yield total/num
#             break
#         except StopIteration:
#             print(">>> 抛出 StopIteration 异常")
#     return total/num

# count_iterator = count()
# count_iterator.send(None) # 激活，此时会运行到 yield 处返回
# count_iterator.send(1) # 从上次 yield 地方继续运行 到下个 yield
# count_iterator.send(2) 
# count_iterator.send(3)
# 停止1,通过Send值得判断来结束，此时会抛出StopIteration异常,return值在exc.value里面
# try:
#     count_iterator.send("stop")   # 
# except StopIteration as exc:
#     print(">>> res",exc.value) # >>> res 1.5
# print(getgeneratorstate(count_iterator)) # GEN_CLOSED

## 停止2,调用 gen.throw()抛出一个异常,如果 gen里面处理了,则返回值会throw的 exception里面
# try:
#     res = count_iterator.throw(StopException)
# except StopIteration as exc:
#     print(">>> res",exc.value) # >>> res 1.5
# print(getgeneratorstate(count_iterator)) # GEN_CLOSED

## 停止3，调用gen.close()方法,不会返回 return值
# res = count_iterator.close()
# print(">>>",res) # None 不会返回 return值
# print(getgeneratorstate(count_iterator)) # GEN_CLOSED


################## 加入 yield from 

# def middle():
#     while True:
#         res = yield from count()
#         print(">>>>>",res)
#         # return res #

# def main():
#     count_iterator =  middle()
#     count_iterator.send(None) # 
#     count_iterator.send(1) # 
#     count_iterator.send(2) 
#     count_iterator.send(3)
#     res = count_iterator.send("stop")  
#     print(res)

# main()
# import asyncio

# def hello_world(loop):
#     """A callback to print 'Hello World' and stop the event loop"""
#     print('Hello World')
#     loop.stop()

# loop = asyncio.get_event_loop()

# # Schedule a call to hello_world()
# loop.call_soon(hello_world, loop)

# # Blocking call interrupted by loop.stop()
# try:
#     loop.run_forever()
# finally:
#     loop.close()



################################# asyncio #############################333

import asyncio
from types import coroutine
loop  = asyncio.get_event_loop()
loop.run_in_executor
print(loop)
async def mock_sleep():
    for i in range(10):
        print(f">>>> 第{i}次执行")
        # print(">>> ready",loop._ready,">>> scheduled",loop._scheduled)
        await asyncio.sleep(1)

if __name__=="__main__":
    # print(loop._ready,loop._scheduled)
    # asyncio.run(mock_sleep())
    t = mock_sleep()
    t.send(None)

###################################### multiple process
# from multiprocessing import Pipe, Process
# x = 1
# y = 3

# def son_process(x, pipe):
#     _out_pipe, _in_pipe = pipe    # 关闭fork过来的输入端
#     _in_pipe.close()
#     while True:
#         try:
#             msg = _out_pipe.recv()
#             print(msg)
#         except EOFError:
#             # 当out_pipe接受不到输出的时候且输入被关闭的时候，会抛出EORFError，可以捕获并且退出子进程
#             break

# if __name__ == '__main__':
#     out_pipe, in_pipe = Pipe(True)
#     son_p = Process(target=son_process, args=(x, (out_pipe, in_pipe)))
#     son_p.start()

#     # 等 pipe 被 fork 后，关闭主进程的输出端
#     # 这样，创建的Pipe一端连接着主进程的输入，一端连接着子进程的输出口
#     out_pipe.close()
#     for x in range(10):
#         in_pipe.send(x)
#     in_pipe.close()
#     son_p.join()
#     print("主进程也结束了")


############################################## subprocess pipe
# import subprocess

# import sys
# def child():    
#     str_= sys.stdin.readlines()
#     print(">>>get std in",str_)


# if __name__ =="__main__":
#     child_p = subprocess.Popen(
#         args=[sys.executable,]
#     )