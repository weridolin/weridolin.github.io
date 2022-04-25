import http.client

def chunk_data(data, chunk_size):
    dl = len(data)
    print(">>>>>>>>>>>>> data length",dl)
    ret = ""
    for i in range(dl // chunk_size):
        ret += "%s\r\n" % (hex(chunk_size)[2:])
        ret += "%s\r\n\r\n" % (data[i * chunk_size : (i + 1) * chunk_size])

    if len(data) % chunk_size != 0:
        ret += "%s\r\n" % (hex(len(data) % chunk_size)[2:])
        ret += "%s\r\n" % (data[-(len(data) % chunk_size):])

    ret += "0\r\n\r\n"
    return ret

body = "TESTDATA"*2
size_per_chunk = 8
conn = http.client.HTTPConnection("127.0.0.1",9999)
url = "/"
conn.putrequest('PUT', url)
conn.putheader('Transfer-Encoding', 'chunked')
# conn.putheader('Connection','close')
conn.endheaders()
conn.send(chunk_data(body, size_per_chunk).encode('utf-8'))
resp = conn.getresponse()
print(resp.status, resp.reason)
import socket
# conn.sock.shutdown(socket.SHUT_WR) # TCP断开四次握手
conn.close()
import time
time.sleep(10)

# import requests,time

# def iter_content():
#     yield b"chunkdata1"
#     yield b"chunkdata2"

# res = requests.put(url="http://127.0.0.1:9999/",data=iter_content())
# print(res.status_code,res.content)
# time.sleep(10)