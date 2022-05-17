## PIPE管道
管道是进程间通信的一种方式.管道分为两种.一种为匿名管道.一种为命名管道.可以用来进行进程间的通信.

#### 匿名管道
- 匿名管道一般是单向流动。它用于一个进程与另一个进程之间的通信。也就是子进程和父进程.一般用来做子进程的输入输出重定向.
- 匿名管道一般用于本地,而不能用于网络.
- 没有所有权和读写权限的控制


#### subprocess.PIPE
subprocess.PIPE中的PIPE用的就是匿名管道。调用*subprocess.popen*时会先去初始化输入输出:
```python

# Parent                   Child
# ------                   -----
# p2cwrite   ---stdin--->  p2cread
# c2pread    <--stdout---  c2pwrite
# errread    <--stderr---  errwrite


class Popen():

    def __init__():
        ...

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        ...

### _get_handles
    if _mswindows:
        #
        # Windows methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            if stdin is None and stdout is None and stderr is None:
                return (-1, -1, -1, -1, -1, -1)

            p2cread, p2cwrite = -1, -1
            c2pread, c2pwrite = -1, -1
            errread, errwrite = -1, -1

            if stdin is None:
                p2cread = _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
                if p2cread is None:
                    p2cread, _ = _winapi.CreatePipe(None, 0)
                    p2cread = Handle(p2cread) # p2cread会作为子进程的s tdTnput
                    _winapi.CloseHandle(_) # 关闭从parent到child的输入。stdin为单向流动，child只能接收，parent无法写入
            elif stdin == PIPE:
                p2cread, p2cwrite = _winapi.CreatePipe(None, 0)
                p2cread, p2cwrite = Handle(p2cread), Handle(p2cwrite) # 双向流动的PIPE，可以从parent写入.child接收,数据为单向流动
            elif stdin == DEVNULL:
                p2cread = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stdin, int):
                p2cread = msvcrt.get_osfhandle(stdin)
            else:
                # Assuming file-like object
                p2cread = msvcrt.get_osfhandle(stdin.fileno())
            p2cread = self._make_inheritable(p2cread)

            if stdout is None:
                c2pwrite = _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
                if c2pwrite is None:
                    _, c2pwrite = _winapi.CreatePipe(None, 0)  # 只保留从child到parent的写通道，数据为单向流动.从child到parent
                    # c2pwrite为子流程的stdout
                    c2pwrite = Handle(c2pwrite)
                    _winapi.CloseHandle(_)
            elif stdout == PIPE:
                c2pread, c2pwrite = _winapi.CreatePipe(None, 0)
                c2pread, c2pwrite = Handle(c2pread), Handle(c2pwrite)
            elif stdout == DEVNULL:
                c2pwrite = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stdout, int):
                c2pwrite = msvcrt.get_osfhandle(stdout)
            else:
                # Assuming file-like object
                c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
            c2pwrite = self._make_inheritable(c2pwrite)

            if stderr is None:
                errwrite = _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
                if errwrite is None:
                    ## errwrite为子流程的输出
                    _, errwrite = _winapi.CreatePipe(None, 0)
                    errwrite = Handle(errwrite)
                    _winapi.CloseHandle(_)
            elif stderr == PIPE:
                errread, errwrite = _winapi.CreatePipe(None, 0)
                errread, errwrite = Handle(errread), Handle(errwrite)
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif stderr == DEVNULL:
                errwrite = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stderr, int):
                errwrite = msvcrt.get_osfhandle(stderr)
            else:
                # Assuming file-like object
                errwrite = msvcrt.get_osfhandle(stderr.fileno())
            errwrite = self._make_inheritable(errwrite)

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


```
- 若想实现从父进程向子进程写入，必须指定stdin=subprocess.PIPE，不指定的话默认只会保留从子进程向父进程写入的通道，而会关闭从父进程向子进程写入的通道.同时，若要获取子进程的输出,必须指定stdput=subprocess.PIPE.否则默认也会关闭父进程读取子进程stdout的读取端（c2pread）      
```python
    ## child.py
    import sys,time
    def child():   
        print("child process start")
        while True: 
            str_= sys.stdin.readline()
            print(">>>get std in",str_)
            time.sleep(1)


    if __name__ =="__main__":
        child()


    ## parent.py
    from asyncio.subprocess import PIPE
    import subprocess,sys,os,time
    if __name__ =="__main__":
        child_file = os.path.join(os.path.dirname(__file__),"child.py")
        child_p = subprocess.Popen(
            args=[sys.executable,child_file],
            # stdin=subprocess.PIPE 
            # stdout=subprocess.PIPE
        )
        ## 如果不指定stdin=subprocess.PIPE,会报 AttributeError: 'NoneType' object has no attribute 'write' 错误
        ## 因为此时从 parent到 child的写入通道被关闭
        for _ in range(10):
            child_p.stdin.write(f"write data:{_}\r\n".encode())
            child_p.stdin.flush()

        ## 如果不指定stdout=subprocess.PIPE,会报 AttributeError: 'NoneType' object has no attribute 'READ' 错误
        ## 因为此时从 c2pwrite的读取通道被关闭
        while child_p.poll() is None:
            output = child_p.stdout.readline()
            print(">>> get child output",output)

```

#### 命名管道
- 命名管道可以使用单向或双向(双工)通信。
- 命名管道可用于在同一台计算机(本地)或不同计算机的网络上提供进程之间的通信。
- 命名管道可以让多个客户端同时连接使用
- 命名管道提供了多个进程之间的双向数据流。
- 有所有权和读写权限的控制

