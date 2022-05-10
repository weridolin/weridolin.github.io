
# from inspect import getgeneratorstate
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