#### wsgi 中支持 websocket
作为一个同步的`http`协议,`wsgi`本身并不支持`websocket`协议.但仍然可以通过中间件的形式,来扩充`wsgi`,使得其同时支持`http`和`websocket`。


##### websocket的握手过程

`websocket`的握手过程可以参考 [websocket](/docs/protocal/websocket/ws.md).简单来说就是：

· a.建立tcp链接
. b.通过http的形式进行`websocket`链接建立`handshake`

##### 基于wsgi的web应用

`wsgi`解析具体可参考[wsgi](/docs/WSGI/1-python原生的wsgi模块.md),根据`wsgi`协议的规范,所有的http请求最终都会通过`wsgi-application(environ,start_response)`来完成处理和返回响应.为了实现`websocket`协议.需要做到

- a. 在`wsgi-application(environ,start_response)`实现websocket的握手协议
- b. 处理完成后,返回请求行和请求头,不关闭当前链接.对应在`wsgi`中就是运行`start_response`返回请求行请求头(参考ws握手协议).然后循环监听socket的输入按照websocket协议处理即可

附:每个websocket链接会长期占用一个sock,请求必须用线程或者异步处理,否则会阻塞其他请求



##### flask中间件扩展

先看看flask-app的调用方法:

```python

class Flask:
    ...

    def wsgi_app(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> cabc.Iterable[bytes]:
        """The actual WSGI application. This is not implemented in
        :meth:`__call__` so that middlewares can be applied without
        losing a reference to the app object. Instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.wsgi_app = MyMiddleware(app.wsgi_app)

        Then you still have the original application object around and
        can continue to call methods on it.

        .. versionchanged:: 0.7
            Teardown events for the request and app contexts are called
            even if an unhandled error occurs. Other events may not be
            called depending on when an error occurs during dispatch.
            See :ref:`callbacks-and-errors`.

        :param environ: A WSGI environment.
        :param start_response: A callable accepting a status code,
            a list of headers, and an optional exception context to
            start the response.
        """
        ctx = self.request_context(environ)
        error: BaseException | None = None
        try:
            try:
                ctx.push()
                response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            except:  # noqa: B001
                error = sys.exc_info()[1]
                raise
            return response(environ, start_response)
        finally:
            if "werkzeug.debug.preserve_context" in environ:
                environ["werkzeug.debug.preserve_context"](_cv_app.get())
                environ["werkzeug.debug.preserve_context"](_cv_request.get())

            if error is not None and self.should_ignore_error(error):
                error = None

            ctx.pop(error)

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> cabc.Iterable[bytes]:
        """The WSGI server calls the Flask application object as the
        WSGI application. This calls :meth:`wsgi_app`, which can be
        wrapped to apply middleware.
        """
        return self.wsgi_app(environ, start_response)


```

按照之前的思路，只需要在 `__call__`方法实现对应的`websocket`的握手逻辑，并持续监听sock的输入即可,按照flask中间件的一个逻辑,简要代码如下:

```python


    class WebsocketMiddleware:
        
    def __init__(self,wsgi_app) -> None:
        self.wsgi_app = wsgi_app ## 原有的 wsgi app
        self.protocols = []

    def __call__(self, environ, start_response):
        ## 模拟 ws的处理情况
        path:str = environ.get("PATH_INFO")
        if not path.startswith("/ws")：
            ### url 以 ws开头。

            ### ws 握手
            self.upgrade_update()## 
            ### 返回响应行和响应头
            headers = [
                ("Upgrade", "websocket"),
                ("Connection", "Upgrade"),
                ("Sec-WebSocket-Accept", "key"),
                ("Sec-WebSocket-Protocol","")
            ]
            start_response("101 Switching Protocols", headers)  ## 返回后，客户端校验通过，链接建立

            ### 循环轮询 输入，按照ws协议解析收到的信息，该请求链接一直建立并没有关闭
            while True:
                read = environ["wsgi.input"].read
                self.get_input(read) 
        else:
            ### 普通http 请求，走原来的 wsgi app
            return self.wsgi_app(environ, start_response)


### 启动 flask
    app = create_app()
    app.wsgi_app = WebsocketMiddleWare(app.wsgi_app) ## 
    app.run(host="127.0.0.1",port=5000,debug=True,use_reloader=True,threaded=True)    

```

上述代码既可完成flask兼容 http 和 ws协议。具体代码可查看:[flask-websocket-middleware]()

##### django 中间件扩展