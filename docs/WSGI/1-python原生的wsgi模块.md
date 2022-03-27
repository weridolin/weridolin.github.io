## 什么是WSGI
因为之前在尝试看django源码的时候，发现有些模块难以理解，因为有必要先学习一下python Web框架比较重要的一个协议，即为*wsgi* 协议，按照官方文档的描述.WSGI不是一个服务器，一个python模块，一个框架，只是服务器和应用程序通信的接口规范。简单来说，就是HTTP 请求到你写的 api(可能为一个函数，或者一个类等等)之间的规范.


### wsgi application
一个符合WSGI协议的APP可以为一个函数，方法，或者类，只要他是一个可调用的对象,即实现了object().call()方法，并且该方法必须拥有如下两个必填输入参数:
1.一个字典对象，包含环境遍历，request请求的参数等等
2.一个响应回调函数，用来发送 HTTP status code/message and HTTP headers 给WSGIServer

除了满足上述两个必要的输入外，一个符合WSGI协议规范的APP，其输出必须为一个*可迭代对象*

```python
from wsgiref.simple_server import make_server

def application(environ, start_response):


    response_body = [
        '%s: %s' % (key, value) for key, value in sorted(environ.items())
    ]
    response_body = '\n'.join(response_body)

    # Adding strings to the response body
    response_body = [
        'The Beggining\n',
        '*' * 30 + '\n',
        response_body,
        '\n' + '*' * 30 ,
        '\nThe End'
    ]

    # So the content-lenght is the sum of all string's lengths
    content_length = sum([len(s) for s in response_body])

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(content_length))
    ]

    # 响应回调函数为可调用对象
    start_response(status, response_headers)
    return response_body

# 启动一个WSGI SERVER
httpd = make_server('localhost', 8051, application)
httpd.handle_request()
```

### 获取request "GET" 的查询参数
请求的参数同样会储存到 *environ* 字典中的 *QUERY_STRING* key里面，同样请求方法会被储存到*REQUEST_METHOD*里面。      
例如    
`get http://localhost:8051/?age=10&hobbies=software&hobbies=tunning`       
则:
`environ["QUERY_STRING"]="age=10&hobbies=software&hobbies=tunning"`             
`environ["REQUEST_METHOD"]='GET'`       
所以其实*environ*到*django/Flask*里面其实就是 *request* object?

### 获取request "POST" body的内容
和获取"GET"的query params参数类似，获取"POST"参数，必须先获取长度，在获取对应的数据     
```python

    # the environment variable CONTENT_LENGTH may be empty or missing
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0

    # When the method is POST the variable will be sent
    # in the HTTP request body which is passed by the WSGI server
    # in the file like wsgi.input environment variable.
    request_body = environ['wsgi.input'].read(request_body_size)

```


## WSGI服务启动
上面的示例例子，我们可以看到启动WSGI服务的代码为：  
```PYTHON
httpd = make_server('localhost', 8051, application)
httpd.handle_request()
```
其中 make_server()的源码为:     
```python
def make_server(
    host, port, app, server_class=WSGIServer, handler_class=WSGIRequestHandler):
    """Create a new WSGI server listening on `host` and `port` for `app`"""
    server = server_class((host, port), handler_class)
    server.set_app(app)
    return server

```     
不难看出，其实就是等价于
```python
server = WSGIServer((host, port),handler_class=WSGIRequestHandler)
server.set_app(application)
```

### WSGIServer
WSGIServer继承自HTTPServer，具体的继承关系为:       
``WSGIServer ---> HTTPServer ---> TCPServer ---> BaseServer ``

源码为:
```python

## WSGIServer
class WSGIServer(HTTPServer):

    """BaseHTTPServer that implements the Python WSGI protocol"""

    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application

## HTTPServer
class HTTPServer(socketserver.TCPServer):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        socketserver.TCPServer.server_bind(self) # == socketserver.TCPServer().server_bind()
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)  # get host domain
        self.server_port = port


```
由此可见，*WSGIServer*是在原有*server_bind*基础上增加*setup_environ*方法，即扩充了环境变量，同时设置了对应的*application*。 
再看*handle_request()* 函数的源码       
```python

    def handle_request(self):
        """Handle one request, possibly blocking.

        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        if timeout is not None:
            deadline = time() + timeout

        # Wait until a request arrives or the timeout expires - the loop is
        # necessary to accommodate early wakeups due to EINTR.
        with _ServerSelector() as selector:
            selector.register(self, selectors.EVENT_READ)

            while True:
                ## select 是一个IO阻塞模型
                ready = selector.select(timeout)
                if ready:
                    return self._handle_request_noblock()
                else:
                    if timeout is not None:
                        timeout = deadline - time()
                        if timeout < 0:
                            return self.handle_timeout()

```
这里应该注意的就是 *_handle_request_noblock（）*方法，代码为：  
```python

    def _handle_request_noblock(self):
        """Handle one request, without blocking.

        I assume that selector.select() has returned that the socket is
        readable before this function was called, so there should be no risk of
        blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except OSError:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except Exception:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
            except:
                self.shutdown_request(request)
                raise
        else:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Call finish_request.

        Overridden by ForkingMixIn and ThreadingMixIn.

        """
        self.finish_request(request, client_address)
        self.shutdown_request(request)

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        self.RequestHandlerClass(request, client_address, self)

```
可以看到，当一个请求到达*WSGISERVER*后，*select IO* 模型会触发，取消阻塞状态.调用的是 RequestHandlerClass(),注意这里会把整个*WSGISERVE*实例传递给RequestHandlerClass


### WSGIRequestHandler
WSGIServer对应 *RequestHandlerClass*为*WSGIRequestHandler*，看一下*init()*的源码
```python
    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

```
WSGIRequestHandler 主要重写了 *handle()*方法
```python 
"""Handle a single HTTP request"""

def handle(self):
    """Handle a single HTTP request"""

    self.raw_requestline = self.rfile.readline(65537)
    if len(self.raw_requestline) > 65536:
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.send_error(414)
        return

    if not self.parse_request(): # An error code has been sent, just exit
        return

    handler = ServerHandler(
        self.rfile, self.wfile, self.get_stderr(), self.get_environ(),
        multithread=False,
    )
    handler.request_handler = self      # backpointer for logging
    handler.run(self.server.get_app())

```
与继承的*BaseHTTPRequestHandler* 的*handle*方法不同，主要是实例化*ServerHandler(self,stdin,stdout,stderr,environ,multithread=True, multiprocess=False)*，并调用*run()* 方法

### ServerHandler
到这里，其实已经可以发现客户端发送一个request实际处理的代码,直接看*serverhandle().run()*的源码，*self.start_response*主要是对status和header进行回调赋值回*serverhandle()*
```python 

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


##  setup_environ()
def setup_environ(self):
    """Set up the environment for one request"""

    env = self.environ = self.os_environ.copy()
    self.add_cgi_vars()

    env['wsgi.input']        = self.get_stdin() 
    env['wsgi.errors']       = self.get_stderr()
    env['wsgi.version']      = self.wsgi_version
    env['wsgi.run_once']     = self.wsgi_run_once
    env['wsgi.url_scheme']   = self.get_scheme()
    env['wsgi.multithread']  = self.wsgi_multithread
    env['wsgi.multiprocess'] = self.wsgi_multiprocess

    if self.wsgi_file_wrapper is not None:
        env['wsgi.file_wrapper'] = self.wsgi_file_wrapper

    if self.origin_server and self.server_software:
        env.setdefault('SERVER_SOFTWARE',self.server_software)


### ServerHandle().start_response()

    def start_response(self, status, headers,exc_info=None):
        """'start_response()' callable as specified by PEP 3333"""

        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
            finally:
                exc_info = None        # avoid dangling circular ref
        elif self.headers is not None:
            raise AssertionError("Headers already set!")

        self.status = status
        self.headers = self.headers_class(headers)
        status = self._convert_string_type(status, "Status")
        assert len(status)>=4,"Status must be at least 4 characters"
        assert status[:3].isdigit(), "Status message must begin w/3-digit code"
        assert status[3]==" ", "Status message must have a space after code"

        if __debug__:
            for name, val in headers:
                name = self._convert_string_type(name, "Header name")
                val = self._convert_string_type(val, "Header value")
                assert not is_hop_by_hop(name),\
                       f"Hop-by-hop header, '{name}: {val}', not allowed"

        return self.write

### 标准的最小单位的 WSGI APPLICATION，这里的start_response对应就是ServerHandle().start_response()方法
def app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['Hello world!\n']



```
还记得一开始是怎么去读取post请求的body的吗，其实就是调用了self.get_stdin() 即 *rfile.read(payload_length)*，并最终将结果写入到*wfile*，这里的*rfile* *wfile*即为一个已经打开的 IO?


#### 关于 *start_response*
WSGI定义的APP的规范的第二个必填参数*start_response*，其实对应的就是*ServerHandle().start_response*方法，通过*ServerHandle().setup_environ()*扩展了一些必要的环境变量。而*start_response*实际运行的就是其实就是`ServerHandle().start_response()`方法.就是把*ServerHandle().start_response()*放在application里面执行. 
这里有两个要注意的地方. 
- 1 WSGI_APPLICATION的返回值其实是赋值给调用该APP的*server handle*实例中的*result*属性。
- 2 start_response其实就是对*ServerHandle*实例中的header,status等赋值，因为是在*WSGIApplication*执行的，所以可以根据*WSGIApplication*的执行结果来传入status, headers(*ServerHandle().start_response()*主要是对status和header进行回调赋值回*serverhandle()*).



### 总结一下
最基础的WSGI服务的，首先是基于基础的TCPServer扩充了一些相关环境变量，并设置对应的application，一个可调用的对象,即url对应的处理函数/示例等。WSGI服务采用select模型来处理网络请求，当接受到请求时,会去实例化一个WSGIRequestHandler对象，同样是重写了handle函数，在handle函数去通过*ServerHandler*来调用一开始定义的application.       
`WSGIServer(注册/定义applicaiton)--> WSGIRequestHandler(示例化会接收WSGIServer实例作为参数)--> ServerHandler(调用WSGIServer中的application(即WSGIRequestHandler中的接受的WSGIServer实例))`

### 补充
#### 1.WSGI的environment变量    
a.cgi(通用网关接口)相关      
- REQUEST_METHOD        
请求方法，比如‘GET’,'POST'...

- SCRIPT_NAME
可以理解为前缀，比如一个app所有的api对应的prefix都为“v1”,即“v1/XXX”,则‘SCRIPT_NAME’即为‘v1’.为空则代表都相对于根域名

- PATH_INFO
即为url相对于域名的地址，比如‘127.0.0.1/asdas/asdad’,PATH_INFO为‘/asdas/asdad’,'127.0.0.1'PATH_INFO为‘则为‘/’.

- QUERY_STRING
url里面的查询参数，比如 “xxx?a=2&b=2”,则‘QUERY_STRING’为a=2&b=2

- CONTENT_TYPE
http请求头字段

- CONTENT_LENGTH
http请求头字段

- SERVER_NAME, SERVER_PORT
/

- SERVER_PROTOCOL
协议，比如‘HTTP/1.0’，‘HTTP/1.1’    

b.WSGI相关    
- wsgi.version
版本，比如（1，0）表示版本为1.0

- wsgi.url_scheme
调用app的服务的协议？比如：https/http

- wsgi.input
用来读取request请求body的stream IO(file-like object), 可以为Serve端的socket IO？

- wsgi.errors
同样是输出流，用来输出错误，对于许多服务器，wsgi.errors 将是服务器的主要错误日志。或者，这可能是sys.stderr或某种类型的log file。服务器的文档应该包括如何配置这个或者在哪里找到记录的输出的说明。如果需要，服务器或网关可以向不同的应用程序提供不同的错误流.

- wsgi.multithread
应用程序对象可以被同一进程中的另一个线程同时调用

- wsgi.multiprocess
如果一个相同的应用程序对象可以同时被另一个进程调用

- wsgi.run_once
如果服务器或网关希望(但不保证!那这个参数有啥用- -)应用程序在其包含的进程的生命周期中只被调用一次，则为true