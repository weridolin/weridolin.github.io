## asgi和wsgi
Asgi,区别于wsgi,是python的一个web异步网关协议.根据[WSGI协议](!'../WSGI/1-python原生的wsgi模块.md'),可知,一个符合WSGI的处理过程是完整的一次同步过程,从 client ---> http server ---> (wsgi) ---> app ---> (wsgi) ---> http server ---> client.是一个一次性的过程,不支持一个长连接(这里是长连接是指app和client之间是keep-alive).比如websocket.
asgi有点类似ws,把一个HTTP请求根据不同阶段拆成对应的事件.放到事件循环中.并交给server的event-loop去驱动运行.


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


## http
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

## http.request event
当client发送了一个HTTP请求时,经过ASGI后,会触发一个**receive**事件,类型为**http.request**,具体结构如下:      

```python
 {
  'type': 'http.request', 
  'body': b'{\r\n    "a":1,\r\n    "b":2\r\n}',  // 请求中的body参数
  'more_body': False
  }

```

## http.response.start/http.response.body event
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

