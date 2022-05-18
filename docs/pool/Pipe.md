## PIPE管道
管道是进程间通信的一种方式.管道分为两种.一种为匿名管道.一种为命名管道.可以用来进行进程间的通信.

#### 匿名管道
- 匿名管道一般是单向流动。它用于一个进程与另一个进程之间的通信。也就是子进程和父进程.一般用来做子进程的输入输出重定向.
- 匿名管道一般用于本地,而不能用于网络.
- 没有所有权和读写权限的控制


#### subprocess.PIPE
subprocess.PIPE中的PIPE用的就是匿名管道。调用*subprocess.popen*时会先去初始化输入输出：⬇️

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
- 命名管道支持异步I/O


#### mutipleProcess.PIPE
multiprocessing.pipe是一个命名管道，其主要是由父进程创建了一个，然后等待多个子进程连接。直接看源码：⬇️
```pythton

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
- 1. 按照命名管道的创建逻辑。先调用*CreateNamedPipe*，创建一个命名管道。并指定管道文件地址，管道模式等相关参数。
- 2. 再创建一个连接客户端,指定连接到打开刚刚创建的PIPE(根据address参数,命名管道会在本地生成一个文件)
- 3. 调用*ConnectNamedPipe*,命名管道h1等待客户端的连接。
- 4. 客户端连接连接后,调用WriteFile()打开管道并向管道中写入一段数据，调用ReadFile可以从管道中读取一段数据.

###### CreateNamedPipe 参数说明
```text

/* 创建命名管道 */
HANDLE WINAPI CreateNamedPipe(
  /**
  * 管道名称。
  * 形式：\\.\pipe\pipename。
  * 最长256个字符，且不区分大小写。
  * 如果已有同名管道，则创建该管道的新实例。
  */
  LPCTSTR lpName, 
  /**
   * 管道打开方式。
   * 常用的管道打开方式有以下三种，更多请查阅MSDN：
   * PIPE_ACCESS_DUPLEX：该管道是双向的，服务器和客户端进程都可以从管道读取或者向管道写入数据。
   * PIPE_ACCESS_INBOUND：该管道中数据是从客户端流向服务端，即客户端只能写，服务端只能读。
   * PIPE_ACCESS_OUTBOUND：该管道中数据是从服务端流向客户端，即客户端只能读，服务端只能写。
  */
  DWORD dwOpenMode,
  /**
   * 管道模式。
   * 常用的管道模式如下，更多请查阅MSDN：
   * PIPE_TYPE_BYTE：数据作为一个连续的字节数据流写入管道。
   * PIPE_TYPE_MESSAGE：数据用数据块（名为“消息”或“报文”）的形式写入管道。
   * PIPE_READMODE_BYTE：数据以单独字节的形式从管道中读出。
   * PIPE_READMODE_MESSAGE：数据以名为“消息”的数据块形式从管道中读出（要求指定PIPE_TYPE_MESSAGE）。
   * PIPE_WAIT：同步操作在等待的时候挂起线程。
   * PIPE_NOWAIT：同步操作立即返回。
  */
  DWORD dwPipeMode,
  /**
   * 该管道能创建的最大实例数。
   * 必须大于1，小于PIPE_UNLIMITED_INSTANCES(255)。
  */
  DWORD nMaxInstances,
  DWORD nOutBufferSize,  // 管道输出缓冲区容量，设置0时使用默认大小,python里面为
  DWORD nInBufferSize,   // 管道输入缓冲区容量，设置0时使用默认大小
  DWORD nDefaultTimeOut, // 管道默认等待超时
  LPSECURITY_ATTRIBUTES lpSecurityAttributes // 管道的安全属性
);

```

##### ConnectNamedPipe参数 

```text

/* 等待客户端连接命名管道 */
BOOL WINAPI ConnectNamedPipe(
  HANDLE hNamedPipe,         // 命名管道的句柄
  LPOVERLAPPED lpOverlapped  // 指向 OVERLAPPED 结构的指针，一般置为NULL即可
);


```

##### createFile参数    

```text

HANDLE CreateFile(
    ## 文件地址
    LPCTSTR lpFileName,    // 指向文件名的指针，可以为地址

    ## 读写权限
    # 0	我们不希望从设备读取数据或向设备写入数据。如果只想改变设备的配置（比如只是修改文件的时间戳），那么可以传0
    # GENERIC_READ	允许对设备进行只读访问
    # GENERIC_WRITE	允许对设备进行只写访问。
    # GENERIC_READ|GENERIC_WRITE	允许对设备进行读写操作.
    DWORD dwDesiredAccess,    // 访问模式（写 / 读） 


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
    DWORD dwShareMode,    // 共享模式 

    ## 安全级别，一般传NULL即可
    LPSECURITY_ATTRIBUTES lpSecurityAttributes, // 指向安全属性的指针 

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
    DWORD dwCreationDisposition,   // 如何创建 

    ## 通信标记，FILE_FLAG_OVERLAPPED 以异步的方式访问设别          
    DWORD dwFlagsAndAttributes,   // 文件属性 

    # 既可以是标识一个打开的文件的句柄，也可以是NULL
    HANDLE hTemplateFile    // 用于复制文件句柄 
);

```

#### 命名管道使用教程
- 1. 服务端(创建方)调用 CreateNamedPipe() 创建命名管道并调用 ConnectNamedPipe() 等待客户端连接。
- 2. 客户端使调用 WaitNamedPipe() / createFile() 连接成功后，再调用 CreateFile() 和 WriteFile() 打开管道并向管道中写入一段数据，即向服务端发送消息。
- 3. 服务端(创建方)调用 ReadFile() 从管道中读取数据后（即收到消息），再向管道中写入确认信息表明已经收到数据，即通知客户端已收到。
- 4. 客户端收到确认信息后结束，调用 CloseHandle()关闭管道（该管道是 CreateFile() 打开的）。服务端使用 DisconnectNamedPipe() 和 CloseHandle() 断开连接并关闭管道。
