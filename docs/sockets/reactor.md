## reactor
基于操作系统的I/O多路复用select,可以同时监听多个socket链接的I/O事件.reactor是基于select的一种网络模型,在我理解更像是一直种网络变成的设计模式。reactor可以分为3个部分:       

- reactor: 负责调用select,轮询socket列表,看是否有读写事件.同时将有读写事件的sock分配到对应的handler处理
- acceptor: 负责处理新的链接
- handler : 负责处理新来的数据和send回复


根据不同的场景需求，reactor可以分为单进程单线程/单进程多线程/多线程多进程3种模式



#### 单进程单线程
这里借助python实现reactor的一个单进程单线程模型:
```python


## 1. reactor 负责调用select轮询各个socket，如果有I/O事件，分发到对应的handler
class SingleProcessSingleThreadReactor:

    handle_map = dict()

    def __init__(self) -> None:
        self.inputs=list()
        self.outputs = list()
        self.exceptions= list()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0) # 设置为非阻塞
        self.server.bind(('0.0.0.0', 8888))
        self.register_self()
    
    def register_self(self):
        self.register_fd(
            self.server,Acceptor(self) # 注册一个acceptor，负责接收新的链接 
        )


    def run_forever(self):
        self.server.listen() # backlog，指定半链接队列的最大长度
        while self.inputs:
            if len(self.inputs) > 512:  # windows系统下select的最大fd个数为512
                if len(self.inputs) % 512==0 :
                    loop_count = int(len(self.inputs)/512) 
                else:
                    loop_count = int(len(self.inputs)/512) + 1
            else:
                loop_count = 1
            for i in range(loop_count):
                try:
                    _inputs = self.inputs[i*512:i*512+512] if i!= loop_count-1 else  self.inputs[i*512:]
                    readable, writable, exceptional = select.select(
                        _inputs,
                        self.outputs, 
                        _inputs+self.outputs) # 
                    print(f"select result --> \n inputs sockets:{readable}. \n outputs sockets:{writable} \n. exceptions sockets:{exceptional}")

                    self.dispatch(readable,writable,exceptional)
                except InterruptedError:
                    break
                except Exception as exc:
                    raise

    def dispatch(self,read_fds,write_fds,exceptions_fds):
        for fd in read_fds:
            handler = self.handle_map.get(fd.fileno())
            handler.handle(fd)

        for fd in write_fds:
            ...

        for fd in exceptions_fds:
            ...

    def register_fd(self,fd,handler):
        if len(self.inputs)> 1024:
            raise ValueError("SELECT 一次性监听的fd个数不能超过1024")
        if not isinstance(fd,int):
            file_no = fd.fileno()
        else:
            file_no = fd
        self.handle_map.update({
            file_no:handler
        })
        self.inputs.append(fd)


    def remove_fd(self,fd):
        if not isinstance(fd,int):
            file_no = fd.fileno()
        else:
            file_no = fd
        if file_no in self.handle_map:
            self.handle_map.pop(file_no)
        if fd in self.inputs:
            self.inputs.remove(fd)
        if fd in self.outputs:
            self.outputs.remove(fd)

#2 handler: 从socket中读取数据  --> 业务处理 --> send回数据
class Handler:
    
    __instance = None

    def __new__(cls,*args,**kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self,reactor=None) -> None:
        self.reactor:SingleProcessSingleThreadReactor = reactor

    def handle(self,sock):
        try:
            data = sock.recv(1024).decode("utf-8")
            if len(data)==0: 
                # 当 socket 的一段关闭时,调用 sock.recv ,会一直收到 O字节的数据 
                # @https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recv
                print(f"socket client:{sock} has closed")
                self.reactor.remove_fd(sock)
            else:
                print(f"socket:{sock} get data:{data}")
                sock.sendall("hello word".encode("utf-8"))

        except ConnectionResetError:
            print(f"socket client:{sock} has close force")
            sock.close()
            self.reactor.remove_fd(sock)

# 3. acceptor:接收新的链接，为新的链接注册新的handler对象

class Acceptor(Handler):

    def handle(self, sock):
        print("before socket accept")
        new_con,addr = sock.accept()
        new_con.setblocking(False)
        print(f"accept a new sock connection:{addr}")
        self.reactor.register_fd(new_con,Handler(reactor=self.reactor))  # 为每个socket注册一个handler


```

因为所有的操作都是在一个线程中，所以可能会出现以下几个缺点:
- 因为只有一个进程，无法充分利用 多核 CPU 的性能；   
- Handler 对象在业务处理时，整个进程是无法处理其他连接的事件的，如果业务处理耗时比较长，那么就造成响应的延迟

实际使用场景： redis对于命令的处理


#### 单进程多线程

单进程多线程的reactor模型，主要是把业务的处理放在了线程中,防止一些耗时的业务操作逻辑影响到reactor调用select对sockets进行轮询.这里也尝试用
python实现了一个简单的单进程多线程reactor模型:      

```python

class SingleProcessMultipleThreadsReactor(SingleProcessSingleThreadReactor):

    def __init__(self,max_worker = None) -> None:
        ## 定义一个线程池用来处理 业务逻辑
        self._executor = ThreadPoolExecutor(max_workers=os.cpu_count() + 4 or max_worker)
        super().__init__()


    def register_self(self):
        # 为server注册一个acceptor处理对象
        self.register_fd(
            self.server,SingleProcessMultipleThreadsAcceptor(self)
        )


class SingleProcessMultipleThreadsHandler(Handler):
    
    def handle(self, sock):
        try:
            data = sock.recv(1024).decode("utf-8")
            if len(data)==0: 
                # 当 socket 的一段关闭时,调用 sock.recv ,会一直收到 O字节的数据 
                # @https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recv
                print(f"socket client:{sock} has closed")
                self.reactor.remove_fd(sock)
            else:
                print(f"socket:{sock} get data:{data}")
                # sock.sendall("hello word".encode("utf-8"))
                assert isinstance(self.reactor,SingleProcessMultipleThreadsReactor)

                ## 模拟在线程池中处理业务逻辑
                fut = self.reactor._executor.submit(
                    self.mock_deal_data_in_thread,data,sock
                )
                ## 处理完成后,发送回复
                fut.add_done_callback(self.finish)

        except ConnectionResetError:
            print(f"socket client:{sock} has close force")
            sock.close()
            self.reactor.remove_fd(sock)
        

    ## 处理业务逻辑
    def mock_deal_data_in_thread(self,data,sock):
        print(f"mock deal data:{data}")
        time.sleep(1)
        return sock

    ## 处理完成后回调，这里没有考虑到 共享数据的互斥 TODO
    def finish(self,fut:Future):
        sock = fut.result()
        sock.sendall("deal finish".encode("utf-8"))


class SingleProcessMultipleThreadsAcceptor(SingleProcessMultipleThreadsHandler):

    def handle(self, sock):
        print("before socket accept")
        new_con,addr = sock.accept()
        new_con.setblocking(False)
        print(f"accept a new sock connection:{addr}")
        # 为每个新建的链接增加一个handler对象
        self.reactor.register_fd(new_con,SingleProcessMultipleThreadsHandler(reactor=self.reactor))


```
