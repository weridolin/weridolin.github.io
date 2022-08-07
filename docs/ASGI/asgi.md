## asgi和wsgi
Asgi,区别于wsgi,是python的一个web异步网关协议.根据[WSGI协议](!'../WSGI/1-python原生的wsgi模块.md'),可知,一个符合WSGI的处理过程是完整的一次同步过程,从 client ---> http server ---> (wsgi) ---> app ---> (wsgi) ---> http server ---> client.是一个一次性的过程,不支持一个长连接(这里是长连接是指app和client之间是keep-alive).比如websocket.
asgi有点类似ws,把一个HTTP请求根据不同阶段拆成对应的事件.放到事件循环中.并交给server的event-loop去驱动运行.      

asgi可以当成wsgi的超集,其可以兼容 *http2/websocket*等协议.


```python 

## 最简单的wsgi app
def test_api(environ,start_response):
    print(">>> exec wsgi application")
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return "exec wsgi application finish"

## wsgi handler.run()
def run(self, application):
    """Invoke the application"""
    # Note to self: don't move the close()!  Asynchronous servers shouldn't
    # call close() from finish_response(), so if you close() anywhere but
    # the double-error branch here, you'll break asynchronous servers by
    # prematurely closing.  Async servers must return from 'run()' without
    # closing if there might still be output to iterate over.
    try:
        self.setup_environ()
        self.result = application(self.environ, self.start_response)
        self.finish_response()
    except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
        # We expect the client to close the connection abruptly from time
        # to time.
        return
    except:
        try:
            self.handle_error()
        except:
            # If we get an error handling an error, just give up already!
            self.close()
            raise   # ...and let the actual server figure it out.

```

而一个基础的符合ASGI协议的app如下:   

```python

# 既然ASGI是异步网关协议.即收到请求后到处理的过程全都是异步的，
import asyncio
async def async_app(scope,receive,send):
    print("get scope >>>",scope)
    event = await receive()
    print("get event >>>",event)
    ## 发送回复必须先发送一个 http.response.start 类型的回复消息
    await send({
            'type': 'http.response.start',   # 
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
        ]   # 发送响应体内容事件
    })
    await send({
        'type': 'http.response.body',   # 发送响应体内容事件
        'body': "response part1".encode("utf-8"),
        'more_body': True  # 代表后面还有消息要返回
    })
    # await asyncio.sleep(3) # 不能使用time.sleep, 会阻塞整个线程
    await send({
        'type': 'http.response.body',
        'body': "response part2".encode("utf-8"),
        'more_body': False # 已经没有内容了，请求可以结束了
    })




```

和WSGI不同,**scope**记录的一些请求信息，类似**WSGI**的**environ**。receive和send都是一个异步的可调用对象，运行时允许被await关键字挂起，ASGI协议规定了他们能够接收和发送的消息事件类型。因为要做到异步，所以所有东西都要转换成 **receive/send event**来驱动。所有的事件驱动由当前线程的event-loop来执行，其中 **recevie** 是用来接收事件,**send**是用来发送事件。

## protocol server 和 Application
ASGI由两部分组成.一为**protocol server**，另外为**ASGI Application**.正如[WSGI]("")一样,由WSGI SERVER和WSGI server组成一样.**protocol**把请求分成了一个个事件.具体可以分为**HTTP**和**WEBSOCKET**.所有的事件都是在**event-loop**里面执行的.

### http
ASGI下一个简单的HTTP请求的scope结果如下,类似于WSGI的environ:

```python
    {'type': 'http', 
    'asgi': {'version': '3.0', 'spec_version': '2.3'}, 
    'http_version': '1.1', 
    'server': ('127.0.0.1', 5000), 
    'client': ('127.0.0.1', 56784), 
    'scheme': 'http', 
    'method': 'GET', 
    'root_path': '', 
    'path': '/', 
    'raw_path': b'/', 
    'query_string': b'a=2',  // 查询参数
    'headers': [
        (b'user-agent', b'PostmanRuntime/7.29.0'), 
        (b'accept', b'*/*'), 
        (b'cache-control', b'no-cache'), 
        (b'postman-token', b'4cd8fa6b-600c-4aee-b5a7-c0945cca8c16'), 
        (b'host', b'0.0.0.0:5000'), 
        (b'accept-encoding', b'gzip, deflate, br'), 
        (b'connection', b'keep-alive')
        ]}
```

#### http.request event
当client发送了一个HTTP请求时,经过ASGI后,会触发一个**receive**事件,类型为**http.request**,具体结构如下:      

```python
 {
  'type': 'http.request', 
  'body': b'{\r\n    "a":1,\r\n    "b":2\r\n}',  // 请求中的body参数
  'more_body': False
  }

```

#### http.response.start/http.response.body event
当asgi-app收到一个**http.request**event,处理完业务逻辑后,通过发送一个类型为**http.response.start**的消息表示开始发送回复.同时必须紧接着发送一个类型的**http.response.body**的回复消息事件,如果只有一个**http.response.start**消息,server是不会发送给**client**的

**http.response.start** 结构必须包括 **status**,**header**字段,结构如下:     
```python
{
    'type': 'http.response.start',   # 
    'status': 200,
    'headers': [[b'content-type', b'application/json']]  
}

```

**http.response.body** 结构必须包括 **body**,**more_body**字段,**more_body**为true表示后续没有回复内容,此时如果在发送类型**http.response.body**的消息,则server会抛出异常
```python
{
    'type': 'http.response.body',
    'body': "response part2".encode("utf-8"),
    'more_body': False # 已经没有内容了，请求可以结束了
}

```

**http.disconnect** 当响应发送完毕(**http.response.body**且**more_body**为false),或者http中途关闭,此时调用了**receive**的话会收到该事件.
```python

    {'type': 'http.disconnect'}

```



**Application** 会在每个 Connection 中被调用一次。Conection 的定义以及其生命周期由协议规范决定。对于 HTTP 来说一个 Connection  就是一次请求,而对于 WebSocket 来说一个 Connection 是一个 WebSocket 连接。


### websocket
##### TODO

## **protocol**:实现asgi的handle
我们都知道,在WSGI中，当一个请求到达服务，会调用 **WSGIHANDLER**进行处理，主要就是根据request上下文，解析成符合WSGI协议的上下文,并且调用了对应的**WSGI app**进行业务逻辑处理。在**ASGI**中,同样也是在**protocol**实现**asgi**协议的转换和调用。   


### channel 库实现ASGI协议

#### customer

customer 可以理解是成符合**ASGI**协议的一个app的抽象,源码如下:
```python

class AsyncConsumer:
    """
    Base consumer class. Implements the ASGI application spec, and adds on
    channel layer management and routing of events to named methods based
    on their type.
    """

    _sync = False
    channel_layer_alias = DEFAULT_CHANNEL_LAYER

    async def __call__(self, scope, receive, send):
        """
        Dispatches incoming messages to type-based handlers asynchronously.
        """
        self.scope = scope


        ## 属于同个channel_layer下的ASGI APP可以相互通讯
        # Initialize channel layer
        self.channel_layer = get_channel_layer(self.channel_layer_alias) # channel应该可以理解为一个域，该域下的所有application可以相互交互 
        if self.channel_layer is not None:
            self.channel_name = await self.channel_layer.new_channel() # 应该是获取某一个域
            self.channel_receive = functools.partial(
                self.channel_layer.receive, self.channel_name
            )
        # Store send function
        if self._sync:
            self.base_send = async_to_sync(send)
        else:
            self.base_send = send
        # Pass messages in from channel layer or client to dispatch method
        try:
            if self.channel_layer is not None: # 如果有 channel_layer，必须监听channel_layer发出的事件(比如广播同一个)。和自身receive的事件
                await await_many_dispatch(
                    [receive, self.channel_receive], self.dispatch 
                )
            else:
                await await_many_dispatch([receive], self.dispatch)
        except StopConsumer:
            # Exit cleanly
            pass

    async def dispatch(self, message):
        """
        Works out what to do with a message.
        """
        handler = getattr(self, get_handler_name(message), None) ## 根据messag type转化成对应的方法,比如 http.request --> http_request
        if handler:
            await handler(message)
        else:
            raise ValueError("No handler for message type %s" % message["type"])

    async def send(self, message):
        """
        Overrideable/callable-by-subclasses send method.
        """
        await self.base_send(message)

    @classmethod
    def as_asgi(cls, **initkwargs):
        """
        Return an ASGI v3 single callable that instantiates a consumer instance
        per scope. Similar in purpose to Django's as_view().

        initkwargs will be used to instantiate the consumer instance.
        """

        async def app(scope, receive, send):
            consumer = cls(**initkwargs)
            return await consumer(scope, receive, send) ## 调用的 __call__ 

        app.consumer_class = cls
        app.consumer_initkwargs = initkwargs

        # take name and docstring from class
        functools.update_wrapper(app, cls, updated=())
        return app

```
* 我们可以知道WSGI协议下app的调用最终调用的就是**app.__call__**,这里可以把**AsyncConsumer**理解为一个符合**asgi**协议的**app**,我们只需要继承该该类，实现对应的事件**处理事件**，比如http协议的话,我们只需要实现对应的**Request/Response Start/Response Body/Disconnect**(ASGI-protocol-SERVER除了HTTP/WS，可以实现自己的任何协议,只要实现对应的AsyncConsumer.handle即可,比如收到的message.type为http.request的话,默认会去找http_request,当然也可以自定义handle逻辑)。
* 根据实际协议完成对应的**AsyncConsumer**后,调用**AsyncConsumer.as_asgi**返回对应的**asgi-app**,当请求进来后,根据路由dispatch到对应的**asgi-app**，调用对应的**_call__**方法。
* **AsyncConsumer.__call__**,逻辑主要是判断该**asgi-app(AsyncConsumer)**是否有对应的**channel_layer**,有的话除了监听**asgi-all.receive**事件,还会监听**channel_layer.receive**事件。我们在看看**await_many_dispatch**的源码，如下，通过源码可以知道,主要就是循环监听了**asgi-app**传进来的**receive**事件和**channel_layer.receive**事件。
```python

async def await_many_dispatch(consumer_callables, dispatch):
    """
    Given a set of consumer callables, awaits on them all and passes results
    from them to the dispatch awaitable as they come in.
    """
    # Start them all off as tasks
    loop = asyncio.get_event_loop() ## 获取or创建一个事件循环
    tasks = [
        loop.create_task(consumer_callable())
        for consumer_callable in consumer_callables #  创建异步task
    ]
    try:
        while True:

            # Wait for any of them to complete
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED) # 等待 receive或者channel_layer.receive产生接收事件
            # Find the completed one(s), yield results, and replace them
            for i, task in enumerate(tasks):
                if task.done():
                    result = task.result()
                    await dispatch(result) # handle  如果接收到 receive event，执行  AsyncConsumer。dispatch,即event-type对应的handle 
                    tasks[i] = asyncio.ensure_future(consumer_callables[i]()) # 继续等待下次receive
    finally:
        # Make sure we clean up tasks on exit # 断开后继续取消所有的 receive事件
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

```


#### channel layer
**channel layer**可以理解为一个域/群组。一个**channel layer**可以包括很多个**channel(Consumer)**,每个**channel layer/group**的结构为:
```python
{group_name:set({channel(Consumer):asyncio.queue})}
```
当出现**asgi-app**需要和其他**asgi-app**交互时，可以通过**channel layer.send**发送,layer层会找到同属于同个name的set(Consumer),并且把消息push到同属于同个**layer/group**对应的channel对应的queue里面去。


#### Router
和所有的**WSGI**的协议的web框架一样,ASGI也有对应的路由设计,可以把路由理解成又对**ASGI-APP**的一层封装.我们先看下channel集成到django中的用法:        
```python

### 请求过来，调用的逻辑为 application._call__()-->ProtocolTypeRouter.__Call__()-->AsgiConsumer.__call__()
application = ProtocolTypeRouter({
  "http": django_asgi_app,
  "websocket": URLRouter(    
    re_path(r'ws/dataFaker/(?P<key>\w+)$',DataFakerConsumer.as_asgi()),
    re_path(r'ws/test/dataFaker/(?P<key>\w+)$',DataFakerConsumer.as_asgi()),
    ),
})

############ URLRouter 源码
class URLRouter:
    """
    Routes to different applications/consumers based on the URL path.

    Works with anything that has a ``path`` key, but intended for WebSocket
    and HTTP. Uses Django's django.urls objects for resolution -
    path() or re_path().
    """

    #: This router wants to do routing based on scope[path] or
    #: scope[path_remaining]. ``path()`` entries in URLRouter should not be
    #: treated as endpoints (ended with ``$``), but similar to ``include()``.
    _path_routing = True

    ## 例子 
    # application = ProtocolTypeRouter({
    #     "http": django_asgi_app,
    #     "websocket": URLRouter(channel_router),
    # })
    # 跟wsgi协议。就是调用的 ProtocolTypeRoute.__call__()

    def __init__(self, routes):
        self.routes = routes

        for route in self.routes:
            # The inner ASGI app wants to do additional routing, route
            # must not be an endpoint
            if getattr(route.callback, "_path_routing", False) is True:
                route.pattern._is_endpoint = False

            if not route.callback and isinstance(route, URLResolver):
                raise ImproperlyConfigured(
                    "%s: include() is not supported in URLRouter. Use nested"
                    " URLRouter instances instead." % (route,)
                )

    async def __call__(self, scope, receive, send):
        # Get the path
        path = scope.get("path_remaining", scope.get("path", None))
        if path is None:
            raise ValueError("No 'path' key in connection scope, cannot route URLs")
        # Remove leading / to match Django's handling
        path = path.lstrip("/")
        # Run through the routes we have until one matches
        for route in self.routes:
            try:
                match = route_pattern_match(route, path)
                if match:
                    new_path, args, kwargs = match
                    # Add args or kwargs into the scope
                    outer = scope.get("url_route", {})
                    application = guarantee_single_callable(route.callback) # 调用对应的 application.__Call__() --> XXX.as_asgi().__call__()
                                                                            # --> consumer.as_asgi()
                    return await application(
                        dict(
                            scope,
                            path_remaining=new_path,
                            url_route={
                                "args": outer.get("args", ()) + args,
                                "kwargs": {**outer.get("kwargs", {}), **kwargs},
                            },
                        ),
                        receive,
                        send, # aaa.as_asgi().__call__()
                    ) ## 调用 __Call__ 进入
            except Resolver404:
                pass
        else:
            if "path_remaining" in scope:
                raise Resolver404("No route found for path %r." % path)
            # We are the outermost URLRouter
            raise ValueError("No route found for path %r." % path)


```
* 我们可以把**URLRouter**也当成一个实现了**asgi**协议的app,当请求请来时，Router根据path找到对应的***app(consumer.as_asgi())***-->调用对应的**app.__call__**，上述的例子调用的过程为**调用的逻辑为 application._call__()-->ProtocolTypeRouter.__Call__()-->AsgiConsumer.__call__()**



我们先通过**uvicorn**这个库来了解从server端到调用asgi-app的调用运行的一个过程。

```python
class Server:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.server_state = ServerState()

        self.started = False
        self.should_exit = False
        self.force_exit = False
        self.last_notified = 0.0

    def run(self, sockets: Optional[List[socket.socket]] = None) -> None:
        ## 创建一个event-loop
        self.config.setup_event_loop()
        return asyncio.run(self.serve(sockets=sockets))# 运行 serve

    async def serve(self, sockets: Optional[List[socket.socket]] = None) -> None:
        process_id = os.getpid()

        config = self.config
        if not config.loaded:
            config.load()

        self.lifespan = config.lifespan_class(config)

        self.install_signal_handlers()

        message = "Started server process [%d]"
        color_message = "Started server process [" + click.style("%d", fg="cyan") + "]"
        logger.info(message, process_id, extra={"color_message": color_message})

        await self.startup(sockets=sockets)
        if self.should_exit:
            return
        await self.main_loop()
        await self.shutdown(sockets=sockets)

        message = "Finished server process [%d]"
        color_message = "Finished server process [" + click.style("%d", fg="cyan") + "]"
        logger.info(message, process_id, extra={"color_message": color_message})

    async def startup(self, sockets: list = None) -> None:
        await self.lifespan.startup()
        if self.lifespan.should_exit:
            self.should_exit = True
            return

        config = self.config

        create_protocol = functools.partial(
            config.http_protocol_class, config=config, server_state=self.server_state
        )
        loop = asyncio.get_running_loop()

        listeners: Sequence[socket.SocketType]
        if sockets is not None:
            # Explicitly passed a list of open sockets.
            # We use this when the server is run from a Gunicorn worker.

            def _share_socket(sock: socket.SocketType) -> socket.SocketType:
                # Windows requires the socket be explicitly shared across
                # multiple workers (processes).
                from socket import fromshare  # type: ignore

                sock_data = sock.share(os.getpid())  # type: ignore
                return fromshare(sock_data)

            self.servers = []
            for sock in sockets:
                if config.workers > 1 and platform.system() == "Windows": ## 多个worker共享一个socket?
                    sock = _share_socket(sock)
                server = await loop.create_server(
                    create_protocol, sock=sock, ssl=config.ssl, backlog=config.backlog
                )
                self.servers.append(server)
            listeners = sockets

        elif config.fd is not None:
            # Use an existing socket, from a file descriptor.
            sock = socket.fromfd(config.fd, socket.AF_UNIX, socket.SOCK_STREAM)
            server = await loop.create_server(
                create_protocol, sock=sock, ssl=config.ssl, backlog=config.backlog
            )
            assert server.sockets is not None  # mypy
            listeners = server.sockets
            self.servers = [server]

        elif config.uds is not None:
            # Create a socket using UNIX domain socket.
            uds_perms = 0o666
            if os.path.exists(config.uds):
                uds_perms = os.stat(config.uds).st_mode
            server = await loop.create_unix_server(
                create_protocol, path=config.uds, ssl=config.ssl, backlog=config.backlog
            )
            os.chmod(config.uds, uds_perms)
            assert server.sockets is not None  # mypy
            listeners = server.sockets
            self.servers = [server]

        else:
            # Standard case. Create a socket from a host/port pair.
            try:
                server = await loop.create_server(
                    create_protocol,
                    host=config.host,
                    port=config.port,
                    ssl=config.ssl,
                    backlog=config.backlog,
                )
            except OSError as exc:
                logger.error(exc)
                await self.lifespan.shutdown()
                sys.exit(1)

            assert server.sockets is not None
            listeners = server.sockets
            self.servers = [server]

        if sockets is None:
            self._log_started_message(listeners)
        else:
            # We're most likely running multiple workers, so a message has already been
            # logged by `config.bind_socket()`.
            pass

        self.started = True

    def _log_started_message(self, listeners: Sequence[socket.SocketType]) -> None:
        config = self.config

        if config.fd is not None:
            sock = listeners[0]
            logger.info(
                "Uvicorn running on socket %s (Press CTRL+C to quit)",
                sock.getsockname(),
            )

        elif config.uds is not None:
            logger.info(
                "Uvicorn running on unix socket %s (Press CTRL+C to quit)", config.uds
            )

        else:
            addr_format = "%s://%s:%d"
            host = "0.0.0.0" if config.host is None else config.host
            if ":" in host:
                # It's an IPv6 address.
                addr_format = "%s://[%s]:%d"

            port = config.port
            if port == 0:
                port = listeners[0].getsockname()[1]

            protocol_name = "https" if config.ssl else "http"
            message = f"Uvicorn running on {addr_format} (Press CTRL+C to quit)"
            color_message = (
                "Uvicorn running on "
                + click.style(addr_format, bold=True)
                + " (Press CTRL+C to quit)"
            )
            logger.info(
                message,
                protocol_name,
                host,
                port,
                extra={"color_message": color_message},
            )

    async def main_loop(self) -> None:
        counter = 0
        should_exit = await self.on_tick(counter)
        while not should_exit: # 这里是维持主进程不退出
            counter += 1
            counter = counter % 864000
            await asyncio.sleep(0.1)
            should_exit = await self.on_tick(counter)

    async def on_tick(self, counter: int) -> bool:
        # Update the default headers, once per second.
        if counter % 10 == 0:
            current_time = time.time()
            current_date = formatdate(current_time, usegmt=True).encode()

            if self.config.date_header:
                date_header = [(b"date", current_date)]
            else:
                date_header = []

            self.server_state.default_headers = (
                date_header + self.config.encoded_headers
            )

            # Callback to `callback_notify` once every `timeout_notify` seconds.
            if self.config.callback_notify is not None:
                if current_time - self.last_notified > self.config.timeout_notify:
                    self.last_notified = current_time
                    await self.config.callback_notify()

        # Determine if we should exit.
        if self.should_exit:
            return True
        if self.config.limit_max_requests is not None:
            ## 当所有请求的个数大于最大限制个数时，退出event-loop?
            return self.server_state.total_requests >= self.config.limit_max_requests
        return False

    async def shutdown(self, sockets: Optional[List[socket.socket]] = None) -> None:
        logger.info("Shutting down")

        # Stop accepting new connections.
        for server in self.servers:
            server.close()
        for sock in sockets or []:
            sock.close()
        for server in self.servers:
            await server.wait_closed()

        # Request shutdown on all existing connections.
        for connection in list(self.server_state.connections):
            connection.shutdown()
        await asyncio.sleep(0.1)

        # Wait for existing connections to finish sending responses.
        if self.server_state.connections and not self.force_exit:
            msg = "Waiting for connections to close. (CTRL+C to force quit)"
            logger.info(msg)
            while self.server_state.connections and not self.force_exit:
                await asyncio.sleep(0.1)

        # Wait for existing tasks to complete.
        if self.server_state.tasks and not self.force_exit:
            msg = "Waiting for background tasks to complete. (CTRL+C to force quit)"
            logger.info(msg)
            while self.server_state.tasks and not self.force_exit: ## 如果不强制退出，则会等到 server_state.tasks 都执行完·
                await asyncio.sleep(0.1)

        # Send the lifespan shutdown event, and wait for application shutdown.
        if not self.force_exit:
            await self.lifespan.shutdown()


                signal.signal(sig, self.handle_exit)

    def handle_exit(self, sig: int, frame: Optional[FrameType]) -> None:

        if self.should_exit and sig == signal.SIGINT:
            self.force_exit = True
        else:
            self.should_exit = True



```
从源码可以看到,serve主要就是调用了run方法，启动了一个event-loop,创建了一个异步socket