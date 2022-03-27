
def test_api(environ,start_response):
    print(">>> exec wsgi application")
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return "exec wsgi application finish"



def interceptor(environ,start_response):
    print("get a request from client") # before call test_api
    result = test_api(environ,start_response)
    print(f"request is finish,result:{result}") # after call test_api
    if isinstance(res,str):
        res = res.encode("utf-8")
    return [res]


from typing import Any
from werkzeug.wsgi import ClosingIterator

import  time
def after_close():
    time.sleep(4)
    print(">>>>>>>>>>>>>>>")

class Interceptor(object):

    def __init__(self,app) -> None:
        self.app = app

    def __call__(self,environ,start_response) -> Any:
        print("get a request from client") # before call test_api
        res =  self.app(environ=environ,start_response=start_response)
        print(f"request is finish,result:{res}") # after call test_api
        # 输出必须为 iter[bytes]
        if isinstance(res,str):
            res = res.encode("utf-8")
        print(res)
        return ClosingIterator(res,[after_close])

# class 



from wsgiref.simple_server import ServerHandler, make_server
# httpd = make_server('localhost', 8051, middleware_func)
httpd = make_server('localhost', 8051, Interceptor(app=test_api))
httpd.handle_request()

