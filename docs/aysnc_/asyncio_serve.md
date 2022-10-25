### 基于asyncio的server的实现
asynico内置了实现server的相关接口.在这里直接对源码进行分析下



#### Server类
asyncio封装了Server的相关接口.这里直接对源码做一个简单的注释说明👇:  

```python

class Server(events.AbstractServer):

    def __init__(self, loop, sockets, protocol_factory, ssl_context, backlog,
                ssl_handshake_timeout):
        self._loop = loop # 对应的事件循环,众所周知,异步中所有的任务都要由事件循环来驱动,server也不例外
        self._sockets = sockets # 监听的sockets server中支持一次性监听多个端口,因为不是阻塞状态
        self._active_count = 0 # 
        self._waiters = [] # 调用 await self.wait_closed 时生成的 future列表(通过设置 fut的状态来控制调用者的执行与否)
        self._protocol_factory = protocol_factory # 这里应该是应用程协议，类似WSGI
        self._backlog = backlog # listen的backlog参数，具体可看sockets部分相关内容
        self._ssl_context = ssl_context  # SSL 上下稳
        self._ssl_handshake_timeout = ssl_handshake_timeout # SSL 握手超时时间
        self._serving = False
        self._serving_forever_fut = None # 这个是为了调用 serve_forever 时用来控制退出

    def __repr__(self):
        return f'<{self.__class__.__name__} sockets={self.sockets!r}>'

    ## 这两个方法作用待定
    def _attach(self):
        assert self._sockets is not None
        self._active_count += 1

    def _detach(self):
        assert self._active_count > 0
        self._active_count -= 1
        if self._active_count == 0 and self._sockets is None:
            self._wakeup()

    # 驱动所有调用了wait_closed的调用方继续运行
    def _wakeup(self):
        waiters = self._waiters
        self._waiters = None
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(waiter)

    def _start_serving(self): # 开启服务监听
        if self._serving:
            return
        self._serving = True
        for sock in self._sockets:
            sock.listen(self._backlog)
            # 调用事件循环loop._start_serving 注册监听的sock到事件循环中。
            self._loop._start_serving(
                self._protocol_factory, sock, self._ssl_context,
                self, self._backlog, self._ssl_handshake_timeout)

    def get_loop(self):
        return self._loop

    def is_serving(self):
        return self._serving

    @property
    def sockets(self): # 监听的服务套接字对象列表
        if self._sockets is None:
            return ()
        return tuple(trsock.TransportSocket(s) for s in self._sockets)

    def close(self): # 关闭服务
        sockets = self._sockets
        if sockets is None:
            return
        self._sockets = None

        for sock in sockets:
            self._loop._stop_serving(sock)

        self._serving = False   


        # 结束serve_forever中的 "await self._serving_forever_fut" 
        if (self._serving_forever_fut is not None and
                not self._serving_forever_fut.done()):
            self._serving_forever_fut.cancel()
            self._serving_forever_fut = None 

        if self._active_count == 0:
            self._wakeup()

    async def start_serving(self): # 开启服务，但马上返回
        self._start_serving()
        # Skip one loop iteration so that all 'loop.add_reader'
        # go through.
        await tasks.sleep(0, loop=self._loop)

    async def serve_forever(self): # 开始服务，并阻塞
        if self._serving_forever_fut is not None:
            raise RuntimeError(
                f'server {self!r} is already being awaited on serve_forever()')
        if self._sockets is None:
            raise RuntimeError(f'server {self!r} is closed')

        self._start_serving()
        self._serving_forever_fut = self._loop.create_future()

        try:
            await self._serving_forever_fut
        except exceptions.CancelledError:
            try:
                self.close()
                await self.wait_closed()
            finally:
                raise
        finally:
            self._serving_forever_fut = None

    async def wait_closed(self): # 等待服务关闭
        if self._sockets is None or self._waiters is None:
            return
        waiter = self._loop.create_future()
        self._waiters.append(waiter)
        await waiter


```



#### BaseSelectorEventLoop 类
select模型是操作系统提供的一种I/O多路复用方式.asyncio实现了**BaseSelectorEventLoop**,这里分成几个部分来说明👇:  

##### reader和waiter
因为异步都是通过事件来驱动的,固每个server的对应各个状态也可以分成各个事件来处理。在asyncio内置的selectEventLoop中,把socket的读写事件封装成对应reader和writer,采用的内置的selectors模块，具体可参考[之前的文章](../python/selectors_/selectors.md)👇:  

- 根据selector.register接口的定义，当调用register(fd, selectors.EVENT_READ,callback)后，对应的callback会对给返回的key.data中
- 在**BaseSelectorEventLoop**中，每个I/O事件对应一个reader和writer. **add_reader**就是对I/O注册的EVENT_READ事件添加一个reader对象.**_add_writer**就是对I/O注册的EVENT_READ事件添加一个writer对象.
- reader/writer会被封装成events.Handle对象，实际事件触发的回调就是一开始调用**add_reader**,**_add_writer**传入的callback.


```python 

class BaseSelectorEventLoop(base_events.BaseEventLoop):
    ### socket在select模型下被分成哪些个事件
    
    ..。
    ## 把事件封装成handler,添加到selector,对于socket来说,

    def _add_reader(self, fd, callback, *args):
        self._check_closed()
        # 传入 event-loop中待执行的方法都会被封装成handler
        handle = events.Handle(callback, args, self, None)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            # 往selector中注册一个套接字.监听Read事件
            self._selector.register(fd, selectors.EVENT_READ,
                                    (handle, None))
                            # 如果 ssock 是可读状态,触发handler        
        else:
            mask, (reader, writer) = key.events, key.data 
                    # (reader, writer) 就是注册传入的 (handle, None)
            self._selector.modify(fd, mask | selectors.EVENT_READ,
                (handle, writer)) # 如果套接字监听已经存在，则只需要把reader改为最新的handler
            if reader is not None: # 取消现有的reader
                reader.cancel()
        return handle

    def _remove_reader(self, fd):
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~selectors.EVENT_READ
            if not mask:
                # 只是监听读事件
                self._selector.unregister(fd)
            else:
                # 监听了读写事件,
                self._selector.modify(fd, mask, (None, writer))

            if reader is not None:
                reader.cancel()
                return True
            else:
                return False

    def _add_writer(self, fd, callback, *args):
        self._check_closed()
        handle = events.Handle(callback, args, self, None)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_WRITE,
                                    (None, handle))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_WRITE,
                                  (reader, handle))
            if writer is not None:
                writer.cancel()
        return handle

    def _remove_writer(self, fd):
        """Remove a writer callback."""
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            # Remove both writer and connector.
            mask &= ~selectors.EVENT_WRITE
            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, (reader, None))

            if writer is not None:
                writer.cancel()
                return True
            else:
                return False

    def add_reader(self, fd, callback, *args):
        """Add a reader callback."""
        self._ensure_fd_no_transport(fd)
        self._add_reader(fd, callback, *args)

    def remove_reader(self, fd):
        """Remove a reader callback."""
        self._ensure_fd_no_transport(fd)
        return self._remove_reader(fd)

    def add_writer(self, fd, callback, *args):
        """Add a writer callback.."""
        self._ensure_fd_no_transport(fd)
        self._add_writer(fd, callback, *args)

    def remove_writer(self, fd):
        """Remove a writer callback."""
        self._ensure_fd_no_transport(fd)
        return self._remove_writer(fd)

    ... 

```

##### 开启服务和监听端口
由asyncio的Server类可知,Server运行的时候，实际上调用的是**loop._start_serve**.我们都知道,开启一个socket监听的过程为绑定端口,开启监听,accept一个新连接.这些逻辑在**BaseSelectorEventLoop**也有基础的实现,直接看源码👇:  

```python

class BaseSelectorEventLoop:
    ...
    # 把已经绑定的sock注册到对应的loop里面
    def _start_serving(self, protocol_factory, sock,
                        sslcontext=None, server=None, backlog=100,
                        ssl_handshake_timeout=constants.SSL_HANDSHAKE_TIMEOUT):
        # 因为bind的端口主要负责accept新的链接请求,所以添加一个
        # 读事件的监听,回调函数为accept一个新请求
        self._add_reader(sock.fileno(), self._accept_connection,
                        protocol_factory, sock, sslcontext, server, backlog,
                        ssl_handshake_timeout)

    def _accept_connection(
            self, 
            protocol_factory,  # 应用层协议。类似WSGI?
            sock, # server对应的socket
            sslcontext=None, 
            server=None, # 封装对应的Serve类。base_events.Server
            backlog=100,
            ssl_handshake_timeout=constants.SSL_HANDSHAKE_TIMEOUT):
        # This method is only called once for each event loop tick where the
        # listening socket has triggered an EVENT_READ. There may be multiple
        # connections waiting for an .accept() so it is called in a loop.
        # See https://bugs.python.org/issue27906 for more details.
        for _ in range(backlog):
            try:
                conn, addr = sock.accept() # 建立socket链接
                if self._debug:
                    logger.debug("%r got a new connection from %r: %r",
                                server, addr, conn)
                conn.setblocking(False) # 设置为非阻塞
            except (BlockingIOError, InterruptedError, ConnectionAbortedError):
                # Early exit because the socket accept buffer is empty.
                return None
            except OSError as exc:
                # There's nowhere to send the error, so just log it.
                if exc.errno in (errno.EMFILE, errno.ENFILE,
                                errno.ENOBUFS, errno.ENOMEM):
                    # Some platforms (e.g. Linux keep reporting the FD as
                    # ready, so we remove the read handler temporarily.
                    # We'll try again in a while.
                    self.call_exception_handler({
                        'message': 'socket.accept() out of system resource',
                        'exception': exc,
                        'socket': trsock.TransportSocket(sock),
                    })
                    # 
                    self._remove_reader(sock.fileno()) # 出现错误，从selector中移除 READ 事件的监听
                    self.call_later(constants.ACCEPT_RETRY_DELAY,# 延迟一段时间后重新尝试
                                    self._start_serving,
                                    protocol_factory, sock, sslcontext, server,
                                    backlog, ssl_handshake_timeout)
                else:
                    raise  # The event loop will catch, log and ignore it.
            else:
                extra = {'peername': addr}
                accept = self._accept_connection2(
                    protocol_factory, conn, extra, sslcontext, server,
                    ssl_handshake_timeout) # 这里是创建一个协程函数不是运行
                self.create_task(accept) # 运行协程函数直到 _accept_connection2 await 处

    async def _accept_connection2(
            self, protocol_factory, conn, extra,
            sslcontext=None, server=None,
            ssl_handshake_timeout=constants.SSL_HANDSHAKE_TIMEOUT):
            # 为新连接的conn创建一个读写监听事件
        protocol = None
        transport = None
        try:
            protocol = protocol_factory() # web app协议？
            waiter = self.create_future()
            if sslcontext:
                transport = self._make_ssl_transport(
                    conn, protocol, sslcontext, waiter=waiter,
                    server_side=True, extra=extra, server=server,
                    ssl_handshake_timeout=ssl_handshake_timeout)
            else:
                ## 初始化会为新的conn添加一个read事件
                transport = self._make_socket_transport(
                    conn, protocol, waiter=waiter, extra=extra,
                    server=server)
            try:
                # 主要就是为了_accept_connection2这一步能够挂起执行
                await waiter
            except BaseException:
                transport.close()
                raise
                # It's now up to the protocol to handle the connection.

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            if self._debug:
                context = {
                    'message':
                        'Error on transport creation for incoming connection',
                    'exception': exc,
                }
                if protocol is not None:
                    context['protocol'] = protocol
                if transport is not None:
                    context['transport'] = transport
                self.call_exception_handler(context)

    def _ensure_fd_no_transport(self, fd):
        # 链接已经建立的情况下不允许修改监听的事件
        fileno = fd
        if not isinstance(fileno, int):
            try:
                fileno = int(fileno.fileno())
            except (AttributeError, TypeError, ValueError):
                # This code matches selectors._fileobj_to_fd function.
                raise ValueError(f"Invalid file object: {fd!r}") from None
        try:
            transport = self._transports[fileno]
        except KeyError:
            pass
        else:
            if not transport.is_closing():
                raise RuntimeError(
                    f'File descriptor {fd!r} is used by transport '
                    f'{transport!r}')

    

```