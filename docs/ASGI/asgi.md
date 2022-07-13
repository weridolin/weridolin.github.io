## asgi网关协议
Asgi,区别于wsgi,是python的一个web异步网关协议.根据[WSGI协议](!'../WSGI/1-python原生的wsgi模块.md'),可知,一个符合WSGI的处理过程是完整的一次同步过程,从 client ---> http server ---> (wsgi) ---> app ---> (wsgi) ---> http server ---> client.是一次不可逆的过程。

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

