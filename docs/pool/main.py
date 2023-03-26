import subprocess
import os,sys
import _winapi
import  time
import msvcrt



child_path = os.path.join(os.path.dirname(__file__),"subp1.py")
# child = subprocess.Popen(
#     args=[sys.executable,child_path],
#     stdout=subprocess.PIPE,
#     stderr=subprocess.PIPE,
#     stdin=subprocess.PIPE
# )
# print(child.communicate()) # 这是个阻塞状态，等到进程运行结束后才会返回输出

####################################### PIPE
# count=0
# pipe = _winapi.CreateNamedPipe(
#     r'\\.\pipe\mypipename',
#     _winapi.PIPE_ACCESS_DUPLEX,
#     _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE | _winapi.PIPE_WAIT,
#     1, 65536, 65536,
#     0,0)
# try:
#     print("waiting for client",pipe)
#     _winapi.ConnectNamedPipe(pipe, 0) # 命名管道必须等到客户端连接了才能写入
#     print("got client")

#     while count < 10:
#         print(f"writing message {count}")
#         # convert to bytes
#         some_data = str.encode(f"{count}")
#         _winapi.WriteFile(pipe, some_data)
#         time.sleep(1)
#         count += 1

#     print("finished now")
# finally:
#     _winapi.CloseHandle(pipe)



################################### Share Memory

from multiprocessing import shared_memory

share = shared_memory.SharedMemory(name="share",size=4096,create=True)
content="共享内容".encode()
print(content.__len__())
share.buf[:content.__len__()]=content
while True:
    time.sleep(1)