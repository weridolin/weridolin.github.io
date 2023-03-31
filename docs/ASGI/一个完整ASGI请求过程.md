这篇文章主要从**uvicorn**和**starlette**源码看一下基于ASGI的整个异步HTTP请求的过程.



#### 第一步 启动一个http服务(uvicorn)
uvicorn是一个高性能的基于asyncio的异步http服务器,可以充当任何实现了asgi协议框架的HTTP服务器.我们直接看uvicorn中的server类。
```python
##uvicorn.server.Server

class Server:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.server_state = ServerState()

        self.started = False
        self.should_exit = False
        self.force_exit = False
        self.last_notified = 0.0

    def run(self, sockets: Optional[List[socket.socket]] = None) -> None:
        self.config.setup_event_loop()
        return asyncio.run(self.serve(sockets=sockets))

    async def serve(self, sockets: Optional[List[socket.socket]] = None) -> None:
        ...

        message = "Started server process [%d]"
        color_message = "Started server process [" + click.style("%d", fg="cyan") + "]"
        logger.info(message, process_id, extra={"color_message": color_message})

        await self.startup(sockets=sockets)
        if self.should_exit:
            return
        await self.main_loop()
        await self.shutdown(sockets=sockets)

        ...

    async def startup(self, sockets: Optional[List[socket.socket]] = None) -> None:
        await self.lifespan.startup()
        if self.lifespan.should_exit:
            self.should_exit = True
            return

        config = self.config

        def create_protocol(
            _loop: Optional[asyncio.AbstractEventLoop] = None,
        ) -> asyncio.Protocol:
            return config.http_protocol_class(  # type: ignore[call-arg]
                config=config,
                server_state=self.server_state,
                app_state=self.lifespan.state,
                _loop=_loop,
            ) # 每个server绑定一个protocol实例

        loop = asyncio.get_running_loop()

        listeners: Sequence[socket.SocketType]
        if sockets is not None:
            # Explicitly passed a list of open sockets.
            # We use this when the server is run from a Gunicorn worker.

            def _share_socket(
                sock: socket.SocketType,
            ) -> socket.SocketType:  # pragma py-linux pragma: py-darwin
                # Windows requires the socket be explicitly shared across
                # multiple workers (processes). # 多个worker监听同个socket?
                from socket import fromshare  # type: ignore[attr-defined]

                sock_data = sock.share(os.getpid())  # type: ignore[attr-defined]
                return fromshare(sock_data)

            self.servers = []
            for sock in sockets:
                if config.workers > 1 and platform.system() == "Windows":
                    sock = _share_socket(  # type: ignore[assignment]
                        sock
                    )  # pragma py-linux pragma: py-darwin
                server = await loop.create_server(
                    create_protocol, sock=sock, ssl=config.ssl, backlog=config.backlog
                )
                self.servers.append(server)
            listeners = sockets

        elif config.fd is not None:  # pragma: py-win32
            # Use an existing socket, from a file descriptor.
            sock = socket.fromfd(config.fd, socket.AF_UNIX, socket.SOCK_STREAM)
            server = await loop.create_server(
                create_protocol, sock=sock, ssl=config.ssl, backlog=config.backlog
            )
            assert server.sockets is not None  # mypy
            listeners = server.sockets
            self.servers = [server]

        elif config.uds is not None:  # pragma: py-win32
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


    async def main_loop(self) -> None:
        counter = 0
        should_exit = await self.on_tick(counter)
        while not should_exit: # 这里是维持主进程不退出,或者根据一些特定条件确实是否退出
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

            ## 修改对应的默认请求头
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
        if self.config.limit_max_requests is not None: # 总的请求大于配置里面最大请求次数限制,直接返回
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
            while self.server_state.tasks and not self.force_exit:
                await asyncio.sleep(0.1)

        # Send the lifespan shutdown event, and wait for application shutdown.
        if not self.force_exit:
            await self.lifespan.shutdown()


```
- 启动server的过程就是调用了**Server.run**方法，也就是调用了**Server.serve**方法.**Server.serve**中最主要的是**self.startup(sockets=sockets)**方法.这个方法是真正绑定监听socket的方法.主要是调用了event-loop中的**create_server**方法.该方法主要是把绑定的socket添加到select队列中.event-loop都会调用select去轮询,如果有新连接进来,调用accept并把新建立的连接添加到select监听队列.具体看[event-loop](/aysnc_/eventloop-futures.md)

- 调用event-loop创建服务后,serve会调用**main_loop**方法，不断进行轮询.根据退出条件判断是否要退出.

至此,一个支持asgi的http异步服务器启动完成.

#### 第二步 接收一个http请求,根据协议进行解析.
当有一个请求到来时.select监听的socket会返回可读事件.event-loop会触发该事件的回调(具体调用栈为`transport._read_ready_cb ---> protocol.data_received`).最终调用的是协议里面的**data_received**方法.

```python 
### uvicorn http1.1 协议实现

class H11Protocol(asyncio.Protocol):
    def __init__(
        self,
        config: Config,
        server_state: ServerState,
        app_state: Dict[str, Any],
        _loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        ...

    def data_received(self, data: bytes) -> None:
        ### 当有socket连接到来时.作为 该socket的READ EVENT的回调函数触发
        self._unset_keepalive_if_required()

        self.conn.receive_data(data)
        self.handle_events()

    def handle_events(self) -> None:
        ## 请求 ---> new connection ---> 服务端要监听的sock+1 ---> select内核调用: (到这一步 ASGI--WSGI)可以都是相同的.
        ## ----> asgi根据不同的event调用不同的处理结果。 这里是WSGI和ASGI的主要不同初.因为asgi采用的异步，遇到异步IO主线程可以去处理其他 connection. 而WSGI只能等到
        ## IO处理完，虽然可以把逻辑放在线程池.butPYTHON的线程是伪线程


        ## sever --> loop.create_server创建监听一个server --(select系统调用)--> 监听socket的accept事件 (回调为 event_loop._accept_connection/event_loop._accept_connection2)
        ## on_accept中创建新的socket连接并且添加到该sock到select队列中.回调函数为 protocol中的data_received/buffer.received  ---> 收到request之后开始调用 asgi application
        ## 直到 request 结束.结束该connection
        
        while True:
            try:
                event = self.conn.next_event() ## 不断去建立的conn里面获取数据和事件
            except h11.RemoteProtocolError:
                msg = "Invalid HTTP request received."
                self.logger.warning(msg)
                self.send_400_response(msg)
                return
            event_type = type(event)

            if event_type is h11.NEED_DATA:
                break

            elif event_type is h11.PAUSED:
                # This case can occur in HTTP pipelining, so we need to
                # stop reading any more data, and ensure that at the end
                # of the active request/response cycle we handle any
                # events that have been buffered up.
                self.flow.pause_reading()
                break

            elif event_type is h11.Request: ## 每当有一个request
                self.headers = [(key.lower(), value) for key, value in event.headers]
                raw_path, _, query_string = event.target.partition(b"?")

                ## 按照asgi协议封装成对应的scope，类似 wsgi 的 environ
                self.scope = {  # type: ignore[typeddict-item] 
                    "type": "http",
                    "asgi": {
                        "version": self.config.asgi_version,
                        "spec_version": "2.3",
                    },
                    "http_version": event.http_version.decode("ascii"),
                    "server": self.server,
                    "client": self.client,
                    "scheme": self.scheme,
                    "method": event.method.decode("ascii"),
                    "root_path": self.root_path,
                    "path": unquote(raw_path.decode("ascii")),
                    "raw_path": raw_path,
                    "query_string": query_string,
                    "headers": self.headers,
                    "state": self.app_state.copy(),
                }

                upgrade = self._get_upgrade()
                if upgrade == b"websocket" and self._should_upgrade_to_ws():
                    self.handle_websocket_upgrade(event)
                    return

                # Handle 503 responses when 'limit_concurrency' is exceeded.
                if self.limit_concurrency is not None and (
                    len(self.connections) >= self.limit_concurrency
                    or len(self.tasks) >= self.limit_concurrency
                ):
                    app = service_unavailable
                    message = "Exceeded concurrency limit."
                    self.logger.warning(message)
                else:
                    app = self.app # ASGI APP

                # 开始调用对应 asgi app，直到request结束，connection关闭
                self.cycle = RequestResponseCycle(
                    scope=self.scope,
                    conn=self.conn,
                    transport=self.transport,
                    flow=self.flow,
                    logger=self.logger,
                    access_logger=self.access_logger,
                    access_log=self.access_log,
                    default_headers=self.server_state.default_headers,
                    message_event=asyncio.Event(),
                    on_response=self.on_response_complete,
                )
                ## asgi app 的运行是直接丢到 loop里面去
                task = self.loop.create_task(self.cycle.run_asgi(app))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)

            elif event_type is h11.Data: ## ASGI接收数据事件
                if self.conn.our_state is h11.DONE:
                    continue
                self.cycle.body += event.data
                if len(self.cycle.body) > HIGH_WATER_LIMIT:
                    self.flow.pause_reading()
                self.cycle.message_event.set()

            elif event_type is h11.EndOfMessage: ##  ASGI执行完成事件
                if self.conn.our_state is h11.DONE:
                    self.transport.resume_reading()
                    self.conn.start_next_cycle()
                    continue
                self.cycle.more_body = False
                self.cycle.message_event.set()


```

- 当request进来时,触发回调,调用协议的中**data_received**方法.接收到数据后.直接调用**handle_events**函数.当事件为**Request.Event**的时候,表示开始处理一个http请求,此时会实例化一个**RequestResponseCycle**对象.并且将其添加到event-loop里面进行调用,通过**cycle.run_asgi(app)**调用对应的**asgi**.当后续有数据到达时,再继续对已经实例化的cycle进行操作,而此时**asgi-app**已经在event-loop中循环.

```python

class RequestResponseCycle:
    def __init__(
        self,
        scope: "HTTPScope",
        conn: h11.Connection,
        transport: asyncio.Transport,
        flow: FlowControl,
        logger: logging.Logger,
        access_logger: logging.Logger,
        access_log: bool,
        default_headers: List[Tuple[bytes, bytes]],
        message_event: asyncio.Event,
        on_response: Callable[..., None],
    ) -> None:
        ...

    # ASGI exception wrapper
    async def run_asgi(self, app: "ASGI3Application") -> None:  # 类似于WSGI的运行方式
        try:
            result = await app(  # type: ignore[func-returns-value]
                self.scope, self.receive, self.send
            )
        except BaseException as exc:
            msg = "Exception in ASGI application\n"
            self.logger.error(msg, exc_info=exc)
            if not self.response_started:
                await self.send_500_response()
            else:
                self.transport.close()
        else:
            if result is not None:
                msg = "ASGI callable should return None, but returned '%s'."
                self.logger.error(msg, result)
                self.transport.close()
            elif not self.response_started and not self.disconnected:  # ASGI协议必须先发送一个 start response的消息
                msg = "ASGI callable returned without starting response."
                self.logger.error(msg)
                await self.send_500_response()
            elif not self.response_complete and not self.disconnected: 
                #  结束的时候没有发送结束消息，这里应该是最后一个 body事件的 more_body 不为true,但是此时asgi app已经运行完成s
                msg = "ASGI callable returned without completing response."
                self.logger.error(msg)
                self.transport.close()
        finally:
            self.on_response = lambda: None
    # ASGI interface
    async def send(self, message: "ASGISendEvent") -> None:
        message_type = message["type"]

        if self.flow.write_paused and not self.disconnected: # 链接未断开且写入流被挂起
            await self.flow.drain()

        if self.disconnected:# 链接断开直接返回
            return

        if not self.response_started: ##  
            # Sending response status line and headers
            if message_type != "http.response.start": #ASGI协议必须先发送一个 response.start的事件
                msg = "Expected ASGI message 'http.response.start', but got '%s'."
                raise RuntimeError(msg % message_type)
            message = cast("HTTPResponseStartEvent", message)

            self.response_started = True
            self.waiting_for_100_continue = False

            status_code = message["status"]
            headers = self.default_headers + list(message.get("headers", []))

            if CLOSE_HEADER in self.scope["headers"] and CLOSE_HEADER not in headers:
                headers = headers + [CLOSE_HEADER]

            if self.access_log:
                self.access_logger.info(
                    '%s - "%s %s HTTP/%s" %d',
                    get_client_addr(self.scope),
                    self.scope["method"],
                    get_path_with_query_string(self.scope),
                    self.scope["http_version"],
                    status_code,
                )

            # Write response status line and headers
            reason = STATUS_PHRASES[status_code]  # 
            event = h11.Response(
                status_code=status_code, headers=headers, reason=reason
            )
            output = self.conn.send(event)
            self.transport.write(output)

        elif not self.response_complete:
            # Sending response body
            if message_type != "http.response.body":
                msg = "Expected ASGI message 'http.response.body', but got '%s'."
                raise RuntimeError(msg % message_type)
            message = cast("HTTPResponseBodyEvent", message)

            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # Write response body
            if self.scope["method"] == "HEAD":
                event = h11.Data(data=b"")
            else:
                event = h11.Data(data=body)
            output = self.conn.send(event)
            self.transport.write(output)

            # Handle response completion
            if not more_body:
                self.response_complete = True
                self.message_event.set()
                event = h11.EndOfMessage()
                output = self.conn.send(event)
                self.transport.write(output)

        else:
            # Response already sent
            msg = "Unexpected ASGI message '%s' sent, after response already completed."
            raise RuntimeError(msg % message_type)

        if self.response_complete:
            if self.conn.our_state is h11.MUST_CLOSE or not self.keep_alive:
                event = h11.ConnectionClosed()
                self.conn.send(event)
                self.transport.close()
            self.on_response()

    async def receive(self) -> "ASGIReceiveEvent":
        if self.waiting_for_100_continue and not self.transport.is_closing():
            event = h11.InformationalResponse(
                status_code=100, headers=[], reason="Continue"
            )
            output = self.conn.send(event)
            self.transport.write(output)
            self.waiting_for_100_continue = False

        if not self.disconnected and not self.response_complete:
            self.flow.resume_reading()
            await self.message_event.wait() # 如果接收到数据,message_event会被set一下，否则会被挂起
            self.message_event.clear() # clear一下，等到下次事件到来

        message: "Union[HTTPDisconnectEvent, HTTPRequestEvent]"
        if self.disconnected or self.response_complete:
            message = {"type": "http.disconnect"}
        else:
            message = {
                "type": "http.request",
                "body": self.body,
                "more_body": self.more_body,
            }
            self.body = b""

        return message

```
- **cycle.run**的核心就是`result = await app(self.scope, self.receive, self.send)`,这里已经可以调用了我们定义的**asgi-app**,同时传入了**received/send**方法.用来在**asgi-app**中和conn交互.当**asgi-app**在运行过程中,如果此时有新的消息(比如request body分多次发送).此时可在**asgi-app**中通过**received**进行获取.

至此,一个request到达异步服务，在通过协议转换为对应的事件,到达了调用的**asgi-app**


#### asgi-application处理对应的request事件,以starlette为例
starlette是一个遵循asgi协议开发的web框架,fastapi框架就是基于此开发的.上面已经说明,一个request请求到来,最终调用的是`result = await app(self.scope, self.receive, self.send)`.其实最终调用的就是。**Starlette.__call__**: 

```python

class Starlette:

    def __init__(
        self: "AppType",
        debug: bool = False,
        routes: typing.Optional[typing.Sequence[BaseRoute]] = None,
        middleware: typing.Optional[typing.Sequence[Middleware]] = None,
        exception_handlers: typing.Optional[
            typing.Mapping[
                typing.Any,
                typing.Callable[
                    [Request, Exception],
                    typing.Union[Response, typing.Awaitable[Response]],
                ],
            ]
        ] = None,
        on_startup: typing.Optional[typing.Sequence[typing.Callable]] = None,
        on_shutdown: typing.Optional[typing.Sequence[typing.Callable]] = None,
        lifespan: typing.Optional[Lifespan["AppType"]] = None,
    ) -> None:
        # The lifespan context function is a newer style that replaces
        # on_startup / on_shutdown handlers. Use one or the other, not both.
        assert lifespan is None or (
            on_startup is None and on_shutdown is None
        ), "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."

        self.debug = debug
        self.state = State()
        self.router = Router(
            routes, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan
        )
        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: typing.Optional[ASGIApp] = None

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler = None
        exception_handlers: typing.Dict[
            typing.Any, typing.Callable[[Request, Exception], Response]
        ] = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers, debug=debug
                )
            ]
        )

        app = self.router
        for cls, options in reversed(middleware):
            app = cls(app=app, **options)
        return app

    @property
    def routes(self) -> typing.List[BaseRoute]:
        return self.router.routes

    # TODO: Make `__name` a positional-only argument when we drop Python 3.7 support.
    def url_path_for(self, __name: str, **path_params: typing.Any) -> URLPath:
        return self.router.url_path_for(__name, **path_params)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, receive, send) # middleware 里面调用的 router 里面的 __call__

    def add_route(
        self,
        path: str,
        route: typing.Callable,
        methods: typing.Optional[typing.List[str]] = None,
        name: typing.Optional[str] = None,
        include_in_schema: bool = True,
    ) -> None:  # pragma: no cover
        self.router.add_route(
            path, route, methods=methods, name=name, include_in_schema=include_in_schema
        )

    def route(
        self,
        path: str,
        methods: typing.Optional[typing.List[str]] = None,
        name: typing.Optional[str] = None,
        include_in_schema: bool = True,
    ) -> typing.Callable:
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> routes = [Route(path, endpoint=...), ...]
        >>> app = Starlette(routes=routes)
        """
        warnings.warn(
            "The `route` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/routing/ for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:
            self.router.add_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator



```
- 直接看**__Call__**方法,先是调用了中间件栈，这点跟[django的中间件](/WSGI/django-middleware.md)设计是一样的.app会先被router封装一层,在被中间件栈封装一层.
- 中间件主要就是对request的到来和返回做一个切面操作，而router的话主要是屏蔽了**received/send**操作。使得最终基于框架实现的接口无需去考虑**received/send**.

```python
## starlette.router
class Router:
    def __init__(
        self,
        routes: typing.Optional[typing.Sequence[BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: typing.Optional[ASGIApp] = None,
        on_startup: typing.Optional[typing.Sequence[typing.Callable]] = None,
        on_shutdown: typing.Optional[typing.Sequence[typing.Callable]] = None,
        # the generic to Lifespan[AppType] is the type of the top level application
        # which the router cannot know statically, so we use typing.Any
        lifespan: typing.Optional[Lifespan[typing.Any]] = None,
    ) -> None:
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

        if on_startup or on_shutdown:
            warnings.warn(
                "The on_startup and on_shutdown parameters are deprecated, and they "
                "will be removed on version 1.0. Use the lifespan parameter instead. "
                "See more about it on https://www.starlette.io/lifespan/.",
                DeprecationWarning,
            )

        if lifespan is None:
            self.lifespan_context: Lifespan = _DefaultLifespan(self)

        elif inspect.isasyncgenfunction(lifespan):
            warnings.warn(
                "async generator function lifespans are deprecated, "
                "use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = asynccontextmanager(
                lifespan,  # type: ignore[arg-type]
            )
        elif inspect.isgeneratorfunction(lifespan):
            warnings.warn(
                "generator function lifespans are deprecated, "
                "use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = _wrap_gen_lifespan_context(
                lifespan,  # type: ignore[arg-type]
            )
        else:
            self.lifespan_context = lifespan
    ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point to the Router class.
        """
        assert scope["type"] in ("http", "websocket", "lifespan")

        if "router" not in scope:
            scope["router"] = self

        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return

        partial = None

        for route in self.routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        if partial is not None:
            #  Handle partial matches. These are cases where an endpoint is
            # able to handle the request, but is not a preferred option.
            # We use this in particular to deal with "405 Method Not Allowed".
            scope.update(partial_scope)
            await partial.handle(scope, receive, send)
            return

        if scope["type"] == "http" and self.redirect_slashes and scope["path"] != "/":
            redirect_scope = dict(scope)
            if scope["path"].endswith("/"):
                redirect_scope["path"] = redirect_scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = redirect_scope["path"] + "/"

            for route in self.routes:
                match, child_scope = route.matches(redirect_scope)
                if match != Match.NONE:
                    redirect_url = URL(scope=redirect_scope)
                    response = RedirectResponse(url=str(redirect_url))
                    await response(scope, receive, send)
                    return

        await self.default(scope, receive, send)

```

- 因为**asgi-app**被router做了一层包装，所以**app.__call__**相当于调用了**router.__call__**,这里会先根据路径,去匹配到对应的路由，同时调用路由对应的处理方法，这里其实就是实际基于框架写的接口.调用代码为` route.handle(scope, receive, send)`

```python

    class Route:
        def __init__(
            self,
            path: str,
            endpoint: typing.Callable,
            *,
            methods: typing.Optional[typing.List[str]] = None,
            name: typing.Optional[str] = None,
            include_in_schema: bool = True,
        ) -> None:
            assert path.startswith("/"), "Routed paths must start with '/'"
            self.path = path
            self.endpoint = endpoint
            self.name = get_name(endpoint) if name is None else name
            self.include_in_schema = include_in_schema

            endpoint_handler = endpoint
            while isinstance(endpoint_handler, functools.partial): ## 处理请求的方法里面加了partial
                endpoint_handler = endpoint_handler.func
            if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
                # Endpoint is function or method. Treat it as `func(request) -> response`.
                self.app = request_response(endpoint) ## 对实际的请求方法再包装一层.跳过 scope/receive/send方法
                if methods is None:
                    methods = ["GET"]
            else:
                # Endpoint is a class. Treat it as ASGI. 参考中间件,实现 __call__(scope,receive,send) 
                self.app = endpoint

            if methods is None:
                self.methods = None
            else:
                self.methods = {method.upper() for method in methods}
                if "GET" in self.methods:
                    self.methods.add("HEAD")

            self.path_regex, self.path_format, self.param_convertors = compile_path(path)


        async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
            ## 匹配到方法后运行对应的方法
            ## 如果是方法，在init的时候已经调用了request_response方法包装了一层
            if self.methods and scope["method"] not in self.methods:
                headers = {"Allow": ", ".join(self.methods)}
                if "app" in scope:
                    raise HTTPException(status_code=405, headers=headers)
                else:
                    response = PlainTextResponse(
                        "Method Not Allowed", status_code=405, headers=headers
                    )
                await response(scope, receive, send)
            else:
                await self.app(scope, receive, send)

```

- handle方法会去判断请求方法是否满足,不满足直接返回,满足的话直接调用了**await self.app(scope, receive, send)**,这里的app在Route初始化时，已经被request_response包装了一层:      

```python

def request_response(func: typing.Callable) -> ASGIApp:
    """
    Takes a function or coroutine `func(request) -> response`,
    and returns an ASGI application.
    """
    is_coroutine = is_async_callable(func)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive=receive, send=send)
        if is_coroutine:
            response = await func(request)
        else:
            response = await run_in_threadpool(func, request)
        await response(scope, receive, send)

    return app
```

- `response = await func(request)`就是最终的调用的基于框架实现的WEB接口.并且屏蔽了`scope, receive, send`,我们在实现的接口里面无需去关心这几个。


至此,一个完整的request请求，到异步HTTP服务，到协议事件的转换，再到对应的**asgi-app**,再到最终实现的接口过程如上
