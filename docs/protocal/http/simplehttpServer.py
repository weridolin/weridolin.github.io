
from http.client import BAD_REQUEST
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
from http import HTTPStatus
from unicodedata import name

### HTTP处理chunk
class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1' # 开启keep-alive,http要使用ThreadingHTTPServer,否则一次性只能处理一个keep-alive连接

    def _read_data(self):
        content_length = int(self.headers['Content-Length']) 
        return self.rfile.read(content_length)          
    
    def do_PUT(self):
        # self._read_data()
        print(self.headers)
        if "Content-Length" in self.headers and "chunked" in self.headers.get("Transfer-Encoding", ""):
            raise AttributeError(">>> 请求头错误")
        if "Content-Length" in self.headers:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            print(">>>> content_length type",body)
        elif "chunked" in self.headers.get("Transfer-Encoding", ""):
            while True:
                line = self.rfile.readline().strip()
                if line:
                    chunk_length = int(line, 16)
                    if chunk_length != 0:
                        chunk = self.rfile.read(chunk_length)
                        # out_file.write(chunk)
                        print(chunk.decode("utf-8"))
                    # Each chunk is followed by an additional empty newline
                    # that we have to consume.
                    self.rfile.readline()
                    # Finally, a chunk size of 0 is an end indication
                    if chunk_length == 0:
                        break
                else:
                    print(">>>> line",line)
        reply_response = {
            "status":HTTPStatus.OK,
            "data":{
                "msg":"success"
            }
        }
        res = json.dumps(reply_response,ensure_ascii=False).encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'application/json')
        self.send_header("Content-length",len(res))
        self.end_headers()
        self.wfile.write(res)         



if __name__ == "__main__":
    TS  = HTTPServer(("127.0.0.1",9999), CustomHTTPRequestHandler)
    TS.serve_forever()