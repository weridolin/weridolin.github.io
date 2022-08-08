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



#### AsyncHttpConsumer
AsyncHttpConsumer是channel提供的http协议的封装，正如上面提到的那样，其继承了**AsyncConsumer**，当我们需要实现一个基于**ASGI**网关协议的HTTP接口时，只需要实现对应的handle方法即可,如下:
```python

### AsyncHttpConsumer 源码
class AsyncHttpConsumer(AsyncConsumer):
    """
    Async HTTP consumer. Provides basic primitives for building asynchronous
    HTTP endpoints.
    """

    def __init__(self, *args, **kwargs):
        self.body = []

    async def send_headers(self, *, status=200, headers=None):
        """
        Sets the HTTP response status and headers. Headers may be provided as
        a list of tuples or as a dictionary.

        Note that the ASGI spec requires that the protocol server only starts
        sending the response to the client after ``self.send_body`` has been
        called the first time.
        """
        if headers is None:
            headers = []
        elif isinstance(headers, dict):
            headers = list(headers.items())

        await self.send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )

    async def send_body(self, body, *, more_body=False):
        """
        Sends a response body to the client. The method expects a bytestring.

        Set ``more_body=True`` if you want to send more body content later.
        The default behavior closes the response, and further messages on
        the channel will be ignored.
        """
        assert isinstance(body, bytes), "Body is not bytes"
        await self.send(
            {"type": "http.response.body", "body": body, "more_body": more_body}
        )

    async def send_response(self, status, body, **kwargs):
        """
        Sends a response to the client. This is a thin wrapper over
        ``self.send_headers`` and ``self.send_body``, and everything said
        above applies here as well. This method may only be called once.
        """
        await self.send_headers(status=status, **kwargs)
        await self.send_body(body)

    async def handle(self, body):
        """
        Receives the request body as a bytestring. Response may be composed
        using the ``self.send*`` methods; the return value of this method is
        thrown away.
        """
        raise NotImplementedError(
            "Subclasses of AsyncHttpConsumer must provide a handle() method."
        )

    async def disconnect(self):
        """
        Overrideable place to run disconnect handling. Do not send anything
        from here.
        """
        pass
        ### receive event

    async def http_request(self, message):# 根据WSGI协议会有请求进来 type为 http.request
        """
        Async entrypoint - concatenates body fragments and hands off control
        to ``self.handle`` when the body has been completely received.


        """
        if "body" in message:
            self.body.append(message["body"])
        if not message.get("more_body"):
            try:
                await self.handle(b"".join(self.body))
            finally:
                await self.disconnect()
                raise StopConsumer()

    async def http_disconnect(self, message):
        """
        Let the user do their cleanup and close the consumer.
        """
        await self.disconnect()
        raise StopConsumer()


######### 实际使用 

#### 继承AsyncHttpConsumer自定义一个consumer

from channels.generic.http import AsyncHttpConsumer

class MyAsyncHttpConsumer(AsyncHttpConsumer):
  ...
  async def handle(self, body):
    print(">>> 处理body",body)
    await self.send_response(200, b"this is response", 
      headers=[
        (b"Content-Type", b"text/plain"),
    ])



#### 标准的最基本的asgi-app
async def async_app(scope,receive,send):
    print("get scope >>>",scope)
    event = await receive()
    print("get event >>>",event)
    # await asyncio.sleep(10)
    await send({
            'type': 'http.response.start',   # 响应头的信息通过这个事件返回，必须发生在body发送之前
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
    # event = await receive()
    print("get event >>>",event)


### DJANGO 中集成
application = ProtocolTypeRouter({
  "http": URLRouter([
      re_path(r'test',MyAsyncHttpConsumer.as_asgi())]), # 调用了as_asgi(),实际就是返回了一个 app(scope,receive,send)
    # "http": URLRouter([
    #   re_path(r'test',async_app)]),
})

```
* 这里要要注意,每个**AsyncHttpConsumer**的**handle**必须通过**send_response**来结束该app的调用，这跟wsgi很相似。
* 实际上,我们跟原生的一个标准**asgi-app**比较一下可以看出,**AsyncHttpConsumer**中的**http_request/send_header/send_body**其实就是按照ASGI-HTTP-PROTOCOL中对应的事件类型抽离出来，等价于receiv/send类型为http.response.start的消息/send类型为http.response.body的消息


#### daphne  -- channel对应的serve
和WSGI一样，除了对应的ASGI-APP外,还必须得有一个对应的ASGI-SERVER.Channel中默认的使用的 daphne作为ASGI-SERVER,实际上当在**settings**中设置的对应的**ASGI_APPLICATION**项后,使用**runserver**，实际上调用的对应的*management/commands/runserver.py*,如下:         
```python 

### 运行runserver调用的方法，这里只贴几个重要方法

class Command(RunserverCommand):
    protocol = "http"
    server_cls = Server

    ...

    def handle(self, *args, **options):
        self.http_timeout = options.get("http_timeout", None)
        self.websocket_handshake_timeout = options.get("websocket_handshake_timeout", 5)
        # Check Channels is installed right
        if options["use_asgi"] and not hasattr(settings, "ASGI_APPLICATION"):
            raise CommandError(
                "You have not set ASGI_APPLICATION, which is needed to run the server."
            )
        # Dispatch upward
        super().handle(*args, **options)

    def inner_run(self, *args, **options):
        # Maybe they want the wsgi one?
        if not options.get("use_asgi", True):
            if hasattr(RunserverCommand, "server_cls"):
                self.server_cls = RunserverCommand.server_cls
            return RunserverCommand.inner_run(self, *args, **options)


        # Run checks 使用ASGI的情况下
        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        self.check_migrations()
        # Print helpful text
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        now = datetime.datetime.now().strftime("%B %d, %Y - %X")
        self.stdout.write(now)
        self.stdout.write(
            (
                "Django version %(version)s, using settings %(settings)r\n"
                "Starting ASGI/Channels version %(channels_version)s development server"
                " at %(protocol)s://%(addr)s:%(port)s/\n"
                "Quit the server with %(quit_command)s.\n"
            )
            % {
                "version": self.get_version(),
                "channels_version": __version__,
                "settings": settings.SETTINGS_MODULE,
                "protocol": self.protocol,
                "addr": "[%s]" % self.addr if self._raw_ipv6 else self.addr,
                "port": self.port,
                "quit_command": quit_command,
            }
        )

        # Launch server in 'main' thread. Signals are disabled as it's still
        # actually a subthread under the autoreloader.
        logger.debug("Daphne running, listening on %s:%s", self.addr, self.port)

        # build the endpoint description string from host/port options
        endpoints = build_endpoint_description_strings(host=self.addr, port=self.port)
        try:
            ## 这里实际上调用到的是daphne中对应的asgi-server
            self.server_cls(
                application=self.get_application(options),
                endpoints=endpoints,
                signal_handlers=not options["use_reloader"],
                action_logger=self.log_action,
                http_timeout=self.http_timeout,
                root_path=getattr(settings, "FORCE_SCRIPT_NAME", "") or "",
                websocket_handshake_timeout=self.websocket_handshake_timeout,
            ).run()

            logger.debug("Daphne exited")
        except KeyboardInterrupt:
            shutdown_message = options.get("shutdown_message", "")
            if shutdown_message:
                self.stdout.write(shutdown_message)
            return

    def get_application(self, options):
        """
        Returns the static files serving application wrapping the default application,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        # get_default_application()就是获取setting里面的 ASGI-APPLICATION配置项
        staticfiles_installed = apps.is_installed("django.contrib.staticfiles")
        use_static_handler = options.get("use_static_handler", staticfiles_installed)
        insecure_serving = options.get("insecure_serving", False)
        if use_static_handler and (settings.DEBUG or insecure_serving):
            return StaticFilesWrapper(get_default_application()) 
        else:
            return get_default_application()


```
* 从源码可以知道,当使用**django admin runserver**时,实际上会去调用到对应的**daphne定义的一个Serve**.如下：

```python 
class Server:
    def __init__(
        self,
        application,
        endpoints=None,
        signal_handlers=True,
        action_logger=None,
        http_timeout=None,
        request_buffer_size=8192,
        websocket_timeout=86400,
        websocket_connect_timeout=20,
        ping_interval=20,
        ping_timeout=30,
        root_path="",
        proxy_forwarded_address_header=None,
        proxy_forwarded_port_header=None,
        proxy_forwarded_proto_header=None,
        verbosity=1,
        websocket_handshake_timeout=5,
        application_close_timeout=10,
        ready_callable=None,
        server_name="daphne",
        # Deprecated and does not work, remove in version 2.2
        ws_protocols=None,
    ):
        self.application = application
        self.endpoints = endpoints or []
        self.listeners = []
        self.listening_addresses = []
        self.signal_handlers = signal_handlers
        self.action_logger = action_logger
        self.http_timeout = http_timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.request_buffer_size = request_buffer_size
        self.proxy_forwarded_address_header = proxy_forwarded_address_header
        self.proxy_forwarded_port_header = proxy_forwarded_port_header
        self.proxy_forwarded_proto_header = proxy_forwarded_proto_header
        self.websocket_timeout = websocket_timeout
        self.websocket_connect_timeout = websocket_connect_timeout
        self.websocket_handshake_timeout = websocket_handshake_timeout
        self.application_close_timeout = application_close_timeout
        self.root_path = root_path
        self.verbosity = verbosity
        self.abort_start = False
        self.ready_callable = ready_callable
        self.server_name = server_name
        # Check our construction is actually sensible
        if not self.endpoints:
            logger.error("No endpoints. This server will not listen on anything.")
            sys.exit(1)

    def run(self):
        # A dict of protocol: {"application_instance":, "connected":, "disconnected":} dicts
        self.connections = {}
        # Make the factory
        self.http_factory = HTTPFactory(self)
        self.ws_factory = WebSocketFactory(self, server=self.server_name)
        self.ws_factory.setProtocolOptions(
            autoPingTimeout=self.ping_timeout,
            allowNullOrigin=True,
            openHandshakeTimeout=self.websocket_handshake_timeout,
        )
        if self.verbosity <= 1:
            # Redirect the Twisted log to nowhere
            globalLogBeginner.beginLoggingTo(
                [lambda _: None], redirectStandardIO=False, discardBuffer=True
            )
        else:
            globalLogBeginner.beginLoggingTo([STDLibLogObserver(__name__)])

        # Detect what Twisted features are enabled
        if http.H2_ENABLED:
            logger.info("HTTP/2 support enabled")
        else:
            logger.info(
                "HTTP/2 support not enabled (install the http2 and tls Twisted extras)"
            )

        # Kick off the timeout loop
        ## reactor 可以直接看成一个对应的event-loop
        reactor.callLater(1, self.application_checker)
        reactor.callLater(2, self.timeout_checker)

        for socket_description in self.endpoints:
            logger.info("Configuring endpoint %s", socket_description)
            ep = serverFromString(reactor, str(socket_description))
            listener = ep.listen(self.http_factory)
            listener.addCallback(self.listen_success)
            listener.addErrback(self.listen_error)
            self.listeners.append(listener)

        # Set the asyncio reactor's event loop as global
        # TODO: Should we instead pass the global one into the reactor?
        asyncio.set_event_loop(reactor._asyncioEventloop)

        # Verbosity 3 turns on asyncio debug to find those blocking yields
        if self.verbosity >= 3:
            asyncio.get_event_loop().set_debug(True)

        reactor.addSystemEventTrigger("before", "shutdown", self.kill_all_applications)
        if not self.abort_start:
            # Trigger the ready flag if we had one
            if self.ready_callable:
                self.ready_callable()
            # Run the reactor
            reactor.run(installSignalHandlers=self.signal_handlers)

    def listen_success(self, port):
        """
        Called when a listen succeeds so we can store port details (if there are any)
        """
        if hasattr(port, "getHost"):
            host = port.getHost()
            if hasattr(host, "host") and hasattr(host, "port"):
                self.listening_addresses.append((host.host, host.port))
                logger.info(
                    "Listening on TCP address %s:%s",
                    port.getHost().host,
                    port.getHost().port,
                )

    def listen_error(self, failure):
        logger.critical("Listen failure: %s", failure.getErrorMessage())
        self.stop()

    def stop(self):
        """
        Force-stops the server.
        """
        if reactor.running:
            reactor.stop()
        else:
            self.abort_start = True

    ### Protocol handling

    def protocol_connected(self, protocol):
        """
        Adds a protocol as a current connection.
        """
        if protocol in self.connections:
            raise RuntimeError("Protocol %r was added to main list twice!" % protocol)
        self.connections[protocol] = {"connected": time.time()}

    def protocol_disconnected(self, protocol):
        # Set its disconnected time (the loops will come and clean it up)
        # Do not set it if it is already set. Overwriting it might
        # cause it to never be cleaned up.
        # See https://github.com/django/channels/issues/1181
        if "disconnected" not in self.connections[protocol]:
            self.connections[protocol]["disconnected"] = time.time()

    ### Internal event/message handling

    def create_application(self, protocol, scope):
        """
        Creates a new application instance that fronts a Protocol instance
        for one of our supported protocols. Pass it the protocol,
        and it will work out the type, supply appropriate callables, and
        return you the application's input queue
        """
        # Make sure the protocol has not had another application made for it
        assert "application_instance" not in self.connections[protocol]
        # Make an instance of the application
        input_queue = asyncio.Queue()
        scope.setdefault("asgi", {"version": "3.0"})

        ### 老方式，调用 asgi-application.__call__,返回一个 future 
        application_instance = self.application(
            scope=scope,
            receive=input_queue.get,# 当server收到HTTP请求时，通过该方法激活 asgi-app
            send=partial(self.handle_reply, protocol), ## 当asgi-app有返回响应时,通过该方法返回给server
        )
        # Run it, and stash the future for later checking
        if protocol not in self.connections:
            return None
        self.connections[protocol]["application_instance"] = asyncio.ensure_future(
            application_instance,
            loop=asyncio.get_event_loop(),
        ) # 这里已经开始运行了 asgi-app,把他扔到事件循环里面去

        ### 返回asgi-app 对应的input-queue。一个已经开始运行的 asgi-app可以当成一个协程,其通过
        ### 一个queue和server进行交互，当有http-event到来时，会push到 input_queue激活协程并继续运行
        return input_queue

    async def handle_reply(self, protocol, message):
        """
        Coroutine that jumps the reply message from asyncio to Twisted
        """
        # Don't do anything if the connection is closed or does not exist
        if protocol not in self.connections or self.connections[protocol].get(
            "disconnected", None
        ):
            return
        try:
            self.check_headers_type(message)
        except ValueError:
            # Ensure to send SOME reply.
            protocol.basic_error(500, b"Server Error", "Server Error")
            raise
        # Let the protocol handle it
        protocol.handle_reply(message)

    @staticmethod
    def check_headers_type(message):
        if not message["type"] == "http.response.start":
            return
        for k, v in message.get("headers", []):
            if not isinstance(k, bytes):
                raise ValueError(
                    "Header name '{}' expected to be `bytes`, but got `{}`".format(
                        k, type(k)
                    )
                )
            if not isinstance(v, bytes):
                raise ValueError(
                    "Header value '{}' expected to be `bytes`, but got `{}`".format(
                        v, type(v)
                    )
                )

    ### Utility

    def application_checker(self):
        """
        Goes through the set of current application Futures and cleans up
        any that are done/prints exceptions for any that errored.
        """
        for protocol, details in list(self.connections.items()):
            disconnected = details.get("disconnected", None)
            application_instance = details.get("application_instance", None)
            # First, see if the protocol disconnected and the app has taken
            # too long to close up
            if (
                disconnected
                and time.time() - disconnected > self.application_close_timeout
            ):
                if application_instance and not application_instance.done():
                    logger.warning(
                        "Application instance %r for connection %s took too long to shut down and was killed.",
                        application_instance,
                        repr(protocol),
                    )
                    application_instance.cancel()
            # Then see if the app is done and we should reap it
            if application_instance and application_instance.done():
                try:
                    exception = application_instance.exception()
                except (CancelledError, asyncio.CancelledError):
                    # Future cancellation. We can ignore this.
                    pass
                else:
                    if exception:
                        if isinstance(exception, KeyboardInterrupt):
                            # Protocol is asking the server to exit (likely during test)
                            self.stop()
                        else:
                            logger.error(
                                "Exception inside application: %s",
                                exception,
                                exc_info=exception,
                            )
                            if not disconnected:
                                protocol.handle_exception(exception)
                del self.connections[protocol]["application_instance"]
                application_instance = None
            # Check to see if protocol is closed and app is closed so we can remove it
            if not application_instance and disconnected:
                del self.connections[protocol]
        reactor.callLater(1, self.application_checker)

    def kill_all_applications(self):
        """
        Kills all application coroutines before reactor exit.
        """
        # Send cancel to all coroutines
        wait_for = []
        for details in self.connections.values():
            application_instance = details["application_instance"]
            if not application_instance.done():
                application_instance.cancel()
                wait_for.append(application_instance)
        logger.info("Killed %i pending application instances", len(wait_for))
        # Make Twisted wait until they're all dead
        wait_deferred = defer.Deferred.fromFuture(asyncio.gather(*wait_for))
        wait_deferred.addErrback(lambda x: None)
        return wait_deferred

    def timeout_checker(self):
        """
        Called periodically to enforce timeout rules on all connections.
        Also checks pings at the same time.
        """
        for protocol in list(self.connections.keys()):
            protocol.check_timeouts()
        reactor.callLater(2, self.timeout_checker)

```
* Server是创建了一个reactor模式的事件循环来运行的,基于twisted(TODO),当SEVER开始运行的时候,获创建一个事件循环并且不断去监听对应的HTTP事件。
* 实例化**asgi-application**是通过**create_application**来实现的,当请求到达**SERVER**时,会调用**protocol**中的**process**方法.即就是**app.__call__**,这里有几个比较重要的入参:
- scope=scope:相当于*wsgi*的*environ*
- receive=input_queue.get:# 当server收到HTTP请求时，通过该方法激活 asgi-app
- send=partial(self.handle_reply, protocol): ## 当asgi-app有返回响应时,通过该方法返回给server
实例化后,*app*其实已经开始运行，并且通过**send/receive**入参跟server交互




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