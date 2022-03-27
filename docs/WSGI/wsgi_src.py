
from wsgiref.simple_server import ServerHandler, make_server,WSGIRequestHandler

def application(environ, start_response):
    ## start_response : BaseHandler.start_response(self, status, headers,exc_info=None)
    print(environ["PATH_INFO"])
    print(environ["QUERY_STRING"])
    print(environ["REQUEST_METHOD"])
    print(environ["SERVER_NAME"],environ["SERVER_PORT"])

    response_body = [
        '%s: %s' % (key, value) for key, value in sorted(environ.items())
    ]
    response_body = '\n'.join(response_body)

    # Adding strings to the response body
    # response_body = [
    #     'The Beggining\n',
    #     '*' * 30 + '\n',
    #     response_body,
    #     '\n' + '*' * 30 ,
    #     '\nThe End'
    # ]
    # So the content-lenght is the sum of all string's lengths
    content_length = sum([len(s) for s in response_body])

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(content_length))
    ]

    start_response(status, response_headers)

    return response_body

httpd = make_server('localhost', 8051, application)
httpd.handle_request()
# WSGIRequestHandler().handle()
# ServerHandler().run()
