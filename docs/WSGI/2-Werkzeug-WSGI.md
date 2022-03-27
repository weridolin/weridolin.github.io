## 引言
从之前的[python原生WSGI模块](1-python原生的wsgi模块.md),我们发现其实我们的application其实粒度只是精细到一个app,一个function。实际情况下我们一般会有多个app,多个function.**Werkzeug-WSGI**正是这样的一个工具库，他并不是协议，而且对app进行了扩充.同时引进了*路由*，*模板*等该概念

## Request Object :对*environ*的扩展
一个只读对象,接受一个*environ*,其中*body*和*header*取自environ，并且提供了各种属性和方法去访问HTTP等相关信息。
#### 入参
- environ   
包含关于服务器配置和客户端请求的信息,由WSGI Server生成

- populate_request  
把该request添加到环境变量*environ['werkzeug.request']*

- shallow 
如果为true，禁止从流中读取各种数据，否则会抛出异常，主要用来防止在中间件中消费数据。


#### Request.application 装饰器
将request作为最后一个参数传给 *view_func()*
```python
### 标准的一个WSGI-APPLICATION
from werkzeug.wrappers import Request, Response

def application(environ, start_response):
    request = Request(environ)
    response = Response(f"Hello {request.args.get('name', 'World!')}!")
    return response(environ, start_response)

### Request.application 代码
    from ..exceptions import HTTPException

    @functools.wraps(f)
    def application(*args):  # type: ignore
        request = cls(args[-2])
        with request:
            try:
                # 把request作为最后一个参数
                resp = f(*args[:-2] + (request,)) # 调用app函数，返回一个response对象
            except HTTPException as e:
                resp = e.get_response(args[-2])
                # 调用response对象
            return resp(*args[-2:])

    return t.cast("WSGIApplication", application)

```


## Response Object: *可调用application*返回值的扩展
表示一个传出的WSGI response，包含正文、状态和报头。具有使用各种HTTP规范定义的功能的属性和方法。Response本身就是一个可调用的application,如下图所示
```python
from werkzeug.wrappers.response import Response

def index():
    return Response("Hello, World!")

def application(environ, start_response):
    path = environ.get("PATH_INFO") or "/"

    if path == "/":
        response = index()
    else:
        response = Response("Not Found", status=404)

    return response(environ, start_response)

```


## Routing ：url匹配，支持多app
```python
## 官方例子

from werkzeug.routing import Map, Rule, NotFound, RequestRedirect

url_map = Map([
    Rule('/', endpoint='blog/index'),
    Rule('/<int:year>/', endpoint='blog/archive'),
    Rule('/<int:year>/<int:month>/', endpoint='blog/archive'),
    Rule('/<int:year>/<int:month>/<int:day>/', endpoint='blog/archive'),
    Rule('/<int:year>/<int:month>/<int:day>/<slug>',
         endpoint='blog/show_post'),
    Rule('/about', endpoint='blog/about_me'),
    Rule('/feeds/', endpoint='blog/feeds'),
    Rule('/feeds/<feed_name>.rss', endpoint='blog/show_feed')
])

def application(environ, start_response):
    urls = url_map.bind_to_environ(environ)
    try:
        endpoint, args = urls.match()
    except HTTPException, e:
        return e(environ, start_response)
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [f'Rule points to {endpoint!r} with arguments {args!r}']

```
- 1. Map：
- 2. Rule
- 3. bind_to_environ()返回一个*MapAdapter*,可以用来匹配当前请求对应的app
- 4. urls.match()返回一个tuple(endpoint, args),endpoint指的为 *wsgi application*,args为参数


## 路由匹配
路由的一般匹配原则为*<converter(arguments):name>*,其中converter为路由转换器,arguments为路由转换器的参数,name为app的参数。例如：
- Rule('/pages/<page>'),
- Rule('/<string(length=2):lang_code>')

### 内置的路由转换器 converters
- UnicodeConverter(map, minlength=1, maxlength=None, length=None)
默认的路由转换器，接受任何字符串作为参数，但是只能有一个路径分割符"/"，所以字符串参数不包括"/".         
Rule('/pages/<page>'), # 默认为“UnicodeConverter”，接受一个string作为path参数
Rule('/<string(length=2):lang_code>') #长度为2，名字为lang_code的string类型的参数

- PathConverter(map, *args, **kwargs)
路径匹配器,跟string类似，但是能够匹配多个“/”        
Rule('/<path:wikipage>')        
Rule('/<path:wikipage>/edit') # 匹配多个 “/”        

- AnyConverter(map, *items)
匹配map中的任何一个item，item可以为PYTHON定义的类型或者字符串       
Rule('/<any(about, help, imprint, class, "foo,bar"):page_name>')

- IntegerConverter(map, fixed_digits=0, min=None, max=None, signed=False)
整形匹配器，fixed_digits为整形位数，比如fixed_digits=3，则“1”对应为“001”. signed为True时，允许接受负数。

- FloatConverter(map, min=None, max=None, signed=False)
浮点型匹配器，当signed为True时，允许接收负数形式的浮点数   
Rule("/offset/<float(signed=True):offset>") # 参数允许为负数 /-0.314

- UUIDConverter(map, *args, **kwargs) 
接收一个UUID字符串

### MapAdapter(map, server_name, script_name, subdomain, url_scheme, path_info, default_method, query_args=None)
Map.bind()和Map.bind_to_environ()返回的结果

- MapAdapter.build():构建完整的url请求路径      
```python
# m = Map([
#     Rule('/', endpoint='index'),
#     Rule('/downloads/', endpoint='downloads/index'),
#     Rule('/downloads/<int:id>', endpoint='downloads/show')
# ])

# urls = m.bind("example.com", "/") # 绑定域名
# urls.build("index", {})
# '/'  

# urls.build("downloads/show", {'id': 42})
# '/downloads/42' #　生成相对的UＲＬ

# urls.build("downloads/show", {'id': 42}, force_external=True)
# 'http://example.com/downloads/42'　＃生成完整的URL >> force_external=True

## 

```
#### build接收只能接收ASCII字符，非ASCII将会根据MAP实例的charset对其进行urlencode处理   
```python
# 空格为非ASCII字符，对其进行urlencode
# urls.build("index", {'q': 'My Searchstring'})
# '/?q=My+Searchstring'
```
#### build构建多个参数的url
```python
# 单个参数多个值
# urls.build("index", {'q': ['a', 'b', 'c']})
# '/?q=a&q=b&q=c'

# 多个参数多个值
# urls.build("index", MultiDict((('p', 'z'), ('q', 'a'), ('q', 'b'))))
# '/?p=z&q=a&q=b'

```

#### match(path_info=None, method=None, return_rule=False, query_args=None, websocket=None)
build()的反过程，返回一个(endpoint, arguments),例如:
```python
# m = Map([
#     Rule('/', endpoint='index'),
#     Rule('/downloads/', endpoint='downloads/index'),
#     Rule('/downloads/<int:id>', endpoint='downloads/show')
# ])

# urls = m.bind("example.com", "/")
# urls.match("/", "GET")
# ('index', {}) # endpoint 来自 Map
# urls.match("/downloads/42")
# ('downloads/show', {'id': 42})

```

### Rule(string, defaults=None, subdomain=None, methods=None, build_only=False, endpoint=None, strict_slashes=None, merge_slashes=None, redirect_to=None, alias=False, host=None, websocket=False)


# Server
主要开始看WSGIRequestHandler

```python

class WSGIRequestHandler(BaseHTTPRequestHandler):
    """A request handler that implements WSGI dispatching."""

    server: "BaseWSGIServer"

    @property
    def server_version(self) -> str:  # type: ignore
        from . import __version__

        return f"Werkzeug/{__version__}"

    def make_environ(self) -> "WSGIEnvironment":
        request_url = url_parse(self.path)

        def shutdown_server() -> None:
            warnings.warn(
                "The 'environ['werkzeug.server.shutdown']' function is"
                " deprecated and will be removed in Werkzeug 2.1.",
                stacklevel=2,
            )
            self.server.shutdown_signal = True

        url_scheme = "http" if self.server.ssl_context is None else "https"

        if not self.client_address:
            self.client_address = ("<local>", 0)
        elif isinstance(self.client_address, str):
            self.client_address = (self.client_address, 0)

        # If there was no scheme but the path started with two slashes,
        # the first segment may have been incorrectly parsed as the
        # netloc, prepend it to the path again.
        if not request_url.scheme and request_url.netloc:
            path_info = f"/{request_url.netloc}{request_url.path}"
        else:
            path_info = request_url.path

        path_info = url_unquote(path_info)

        environ: "WSGIEnvironment" = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": url_scheme,
            "wsgi.input": self.rfile,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": self.server.multithread,
            "wsgi.multiprocess": self.server.multiprocess,
            "wsgi.run_once": False,
            "werkzeug.server.shutdown": shutdown_server,
            "werkzeug.socket": self.connection,
            "SERVER_SOFTWARE": self.server_version,
            "REQUEST_METHOD": self.command,
            "SCRIPT_NAME": "",
            "PATH_INFO": _wsgi_encoding_dance(path_info),
            "QUERY_STRING": _wsgi_encoding_dance(request_url.query),
            # Non-standard, added by mod_wsgi, uWSGI
            "REQUEST_URI": _wsgi_encoding_dance(self.path),
            # Non-standard, added by gunicorn
            "RAW_URI": _wsgi_encoding_dance(self.path),
            "REMOTE_ADDR": self.address_string(),
            "REMOTE_PORT": self.port_integer(),
            "SERVER_NAME": self.server.server_address[0],
            "SERVER_PORT": str(self.server.server_address[1]),
            "SERVER_PROTOCOL": self.request_version,
        }

        for key, value in self.headers.items():
            key = key.upper().replace("-", "_")
            value = value.replace("\r\n", "")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = f"HTTP_{key}"
                if key in environ:
                    value = f"{environ[key]},{value}"
            environ[key] = value

        if environ.get("HTTP_TRANSFER_ENCODING", "").strip().lower() == "chunked":
            environ["wsgi.input_terminated"] = True
            environ["wsgi.input"] = DechunkedInput(environ["wsgi.input"])

        # Per RFC 2616, if the URL is absolute, use that as the host.
        # We're using "has a scheme" to indicate an absolute URL.
        if request_url.scheme and request_url.netloc:
            environ["HTTP_HOST"] = request_url.netloc

        try:
            # binary_form=False gives nicer information, but wouldn't be compatible with
            # what Nginx or Apache could return.
            peer_cert = self.connection.getpeercert(binary_form=True)
            if peer_cert is not None:
                # Nginx and Apache use PEM format.
                environ["SSL_CLIENT_CERT"] = ssl.DER_cert_to_PEM_cert(peer_cert)
        except ValueError:
            # SSL handshake hasn't finished.
            self.server.log("error", "Cannot fetch SSL peer certificate info")
        except AttributeError:
            # Not using TLS, the socket will not have getpeercert().
            pass

        return environ

    def run_wsgi(self) -> None:
        if self.headers.get("Expect", "").lower().strip() == "100-continue":
            self.wfile.write(b"HTTP/1.1 100 Continue\r\n\r\n")

        self.environ = environ = self.make_environ()
        status_set: t.Optional[str] = None
        headers_set: t.Optional[t.List[t.Tuple[str, str]]] = None
        status_sent: t.Optional[str] = None
        headers_sent: t.Optional[t.List[t.Tuple[str, str]]] = None

        def write(data: bytes) -> None:
            nonlocal status_sent, headers_sent
            assert status_set is not None, "write() before start_response"
            assert headers_set is not None, "write() before start_response"
            if status_sent is None:
                status_sent = status_set
                headers_sent = headers_set
                try:
                    code_str, msg = status_sent.split(None, 1)
                except ValueError:
                    code_str, msg = status_sent, ""
                code = int(code_str)
                self.send_response(code, msg)
                header_keys = set()
                for key, value in headers_sent:
                    self.send_header(key, value)
                    key = key.lower()
                    header_keys.add(key)
                if not (
                    "content-length" in header_keys
                    or environ["REQUEST_METHOD"] == "HEAD"
                    or code < 200
                    or code in (204, 304)
                ):
                    self.close_connection = True
                    self.send_header("Connection", "close")
                if "server" not in header_keys:
                    self.send_header("Server", self.version_string())
                if "date" not in header_keys:
                    self.send_header("Date", self.date_time_string())
                self.end_headers()

            assert isinstance(data, bytes), "applications must write bytes"
            self.wfile.write(data)
            self.wfile.flush()

        def start_response(status, headers, exc_info=None):  # type: ignore
            nonlocal status_set, headers_set
            if exc_info:
                try:
                    if headers_sent:
                        raise exc_info[1].with_traceback(exc_info[2])
                finally:
                    exc_info = None
            elif headers_set:
                raise AssertionError("Headers already set")
            status_set = status
            headers_set = headers
            return write

        def execute(app: "WSGIApplication") -> None:
            application_iter = app(environ, start_response)
            try:
                for data in application_iter:
                    write(data)
                if not headers_sent:
                    write(b"")
            finally:
                if hasattr(application_iter, "close"):
                    application_iter.close()  # type: ignore

        try:
            execute(self.server.app)
        except (ConnectionError, socket.timeout) as e:
            self.connection_dropped(e, environ)
        except Exception:
            if self.server.passthrough_errors:
                raise
            from .debug.tbtools import get_current_traceback

            traceback = get_current_traceback(ignore_system_exceptions=True)
            try:
                # if we haven't yet sent the headers but they are set
                # we roll back to be able to set them again.
                if status_sent is None:
                    status_set = None
                    headers_set = None
                execute(InternalServerError())
            except Exception:
                pass
            self.server.log("error", "Error on request:\n%s", traceback.plaintext)

    def handle(self) -> None:
        """Handles a request ignoring dropped connections."""
        try:
            BaseHTTPRequestHandler.handle(self)
        except (ConnectionError, socket.timeout) as e:
            self.connection_dropped(e)
        except Exception as e:
            if self.server.ssl_context is not None and is_ssl_error(e):
                self.log_error("SSL error occurred: %s", e)
            else:
                raise
        if self.server.shutdown_signal:
            self.initiate_shutdown()

    def initiate_shutdown(self) -> None:
        if is_running_from_reloader():
            # Windows does not provide SIGKILL, go with SIGTERM then.
            sig = getattr(signal, "SIGKILL", signal.SIGTERM)
            os.kill(os.getpid(), sig)

        self.server._BaseServer__shutdown_request = True  # type: ignore

    def connection_dropped(
        self, error: BaseException, environ: t.Optional["WSGIEnvironment"] = None
    ) -> None:
        """Called if the connection was closed by the client.  By default
        nothing happens.
        """

    def handle_one_request(self) -> None:
        """Handle a single HTTP request."""
        self.raw_requestline = self.rfile.readline() # HTTP协议解析，解析第一行,具体参考HTTP协议头格式
        if not self.raw_requestline:
            self.close_connection = True
        elif self.parse_request(): # 解析HTTP协议头
            self.run_wsgi() # 调用application

    def send_response(self, code: int, message: t.Optional[str] = None) -> None:
        """Send the response header and log the response code."""
        self.log_request(code)
        if message is None:
            message = self.responses[code][0] if code in self.responses else ""
        if self.request_version != "HTTP/0.9":
            hdr = f"{self.protocol_version} {code} {message}\r\n"
            self.wfile.write(hdr.encode("ascii"))

    def version_string(self) -> str:
        return super().version_string().strip()

    def address_string(self) -> str:
        if getattr(self, "environ", None):
            return self.environ["REMOTE_ADDR"]  # type: ignore

        if not self.client_address:
            return "<local>"

        return self.client_address[0]

    def port_integer(self) -> int:
        return self.client_address[1]

    def log_request(
        self, code: t.Union[int, str] = "-", size: t.Union[int, str] = "-"
    ) -> None:
        try:
            path = uri_to_iri(self.path)
            msg = f"{self.command} {path} {self.request_version}"
        except AttributeError:
            # path isn't set if the requestline was bad
            msg = self.requestline

        code = str(code)

        if _log_add_style:
            if code[0] == "1":  # 1xx - Informational
                msg = _ansi_style(msg, "bold")
            elif code == "200":  # 2xx - Success
                pass
            elif code == "304":  # 304 - Resource Not Modified
                msg = _ansi_style(msg, "cyan")
            elif code[0] == "3":  # 3xx - Redirection
                msg = _ansi_style(msg, "green")
            elif code == "404":  # 404 - Resource Not Found
                msg = _ansi_style(msg, "yellow")
            elif code[0] == "4":  # 4xx - Client Error
                msg = _ansi_style(msg, "bold", "red")
            else:  # 5xx, or any other response
                msg = _ansi_style(msg, "bold", "magenta")

        self.log("info", '"%s" %s %s', msg, code, size)

    def log_error(self, format: str, *args: t.Any) -> None:
        self.log("error", format, *args)

    def log_message(self, format: str, *args: t.Any) -> None:
        self.log("info", format, *args)

    def log(self, type: str, message: str, *args: t.Any) -> None:
        _log(
            type,
            f"{self.address_string()} - - [{self.log_date_time_string()}] {message}\n",
            *args,
        )

```
跟python原生的WSGI处理流程相似.一个request最终对应的请求方式还是调用*WSGIRequestHandler.handle()*函数-->调用*WSGIRequestHandler.handle_one_request()(先解析HTTP协议)*-->*WSGIRequestHandler.run_wsgi()(运行wsgi application)*
定位到run_wsgi



# Response
werkzeug又对python的原生WSGI返回的iterator[bytes]做了一层封装.官方给的例子是:

```python

def index():
    return Response("Hello, World!")

def application(environ, start_response):
    path = environ.get("PATH_INFO") or "/"

    if path == "/":
        response = index()
    else:
        response = Response("Not Found", status=404)

    return response(environ, start_response)

```
固response必须是一个可callable对象，同样必须符合WSGI规范

```python

#### 这里截取了Response部分代码

class Response():

    ...

    def get_app_iter(self, environ: "WSGIEnvironment") -> t.Iterable[bytes]:
        """Returns the application iterator for the given environ.  Depending
        on the request method and the current status code the return value
        might be an empty response rather than the one from the response.

        If the request method is `HEAD` or the status code is in a range
        where the HTTP specification requires an empty response, an empty
        iterable is returned.

        .. versionadded:: 0.6

        :param environ: the WSGI environment of the request.
        :return: a response iterable.
        """
        status = self.status_code
        if (
            environ["REQUEST_METHOD"] == "HEAD"
            or 100 <= status < 200
            or status in (204, 304)
        ):
            iterable: t.Iterable[bytes] = ()
        elif self.direct_passthrough:
            if __debug__:
                _warn_if_string(self.response)
            return self.response  # type: ignore
        else:
            iterable = self.iter_encoded()
        return ClosingIterator(iterable, self.close)

    def get_wsgi_response(
        self, environ: "WSGIEnvironment"
    ) -> t.Tuple[t.Iterable[bytes], str, t.List[t.Tuple[str, str]]]:
        """Returns the final WSGI response as tuple.  The first item in
        the tuple is the application iterator, the second the status and
        the third the list of headers.  The response returned is created
        specially for the given environment.  For example if the request
        method in the WSGI environment is ``'HEAD'`` the response will
        be empty and only the headers and status code will be present.

        .. versionadded:: 0.6

        :param environ: the WSGI environment of the request.
        :return: an ``(app_iter, status, headers)`` tuple.
        """
        headers = self.get_wsgi_headers(environ)
        app_iter = self.get_app_iter(environ)
        return app_iter, self.status, headers.to_wsgi_list()

    def __call__(
        self, environ: "WSGIEnvironment", start_response: "StartResponse"
    ) -> t.Iterable[bytes]:
        """Process this response as WSGI application.

        :param environ: the WSGI environment.
        :param start_response: the response callable provided by the WSGI
                               server.
        :return: an application iterator
        """
        app_iter, status, headers = self.get_wsgi_response(environ)
        start_response(status, headers)
        return app_iter

    ...

    def close(self) -> None:
        """Close the wrapped response if possible.  You can also use the object
        in a with statement which will automatically close it.

        .. versionadded:: 0.9
           Can now be used in a with statement.
        """
        if hasattr(self.response, "close"):
            self.response.close()  # type: ignore
        for func in self._on_close:
            func()
```
这里主要是 `app_iter, status, headers = self.get_wsgi_response(environ)`,这里返回的是一个ClosingIterator()对象,我们再看ClosingIterator的代码
```python 
## ClosingIterator
class ClosingIterator:
    def __init__(
        self,
        iterable: t.Iterable[bytes],
        callbacks: t.Optional[
            t.Union[t.Callable[[], None], t.Iterable[t.Callable[[], None]]]
        ] = None,
    ) -> None:
        iterator = iter(iterable)
        self._next = t.cast(t.Callable[[], bytes], partial(next, iterator))
        if callbacks is None:
            callbacks = []
        elif callable(callbacks):
            callbacks = [callbacks]
        else:
            callbacks = list(callbacks)
        iterable_close = getattr(iterable, "close", None)
        if iterable_close:
            callbacks.insert(0, iterable_close)
        self._callbacks = callbacks

    def __iter__(self) -> "ClosingIterator":
        return self

    def __next__(self) -> bytes:
        return self._next()

    def close(self) -> None:
        for callback in self._callbacks:
            callback()
```
这里主要还是扩展了一个callbacks属性，并且定义了close方法，*close*方法将在上面提到的*WSGIRequestHandler.run_wsgi()*中被调用.
```python
    def execute(app: "WSGIApplication") -> None:
        application_iter = app(environ, start_response)
        try:
            for data in application_iter: ## 这里调用的就是ClosingIterator.next()
                write(data)
            if not headers_sent:
                write(b"")
        finally:
            if hasattr(application_iter, "close"): # 调用了ClosingIterator.close()
                application_iter.close()  # type: ignore
```
再通过*ClosingIterator(iterable, self.close)*可以得出，*application_iter.close()*对应的就是response.close()这是在return了响应数据后做的操作.不影响到响应时间..

