
path = "https://cn.bing.com/search?q=python%20BaseHTTPRequestHandler%20get%20post%20body&qs=n&form=QBRE&=%25eManage%20Your%20Search%20History%25E&sp=-1&pq=python%20basehttprequesthandler%20get%20post%20b&sc=0-40&sk=&cvid=A3C1D47F9FD34DFCAC77325EE5BF49D1"
# path = path.split('?',1)[0]
# print(path)
# path = path.split('#',1)[0]
# print(path)
import urllib.parse
# path = urllib.parse.unquote(path, errors='surrogatepass')
# print(path)
parts = urllib.parse.urlsplit(path)
print(parts)