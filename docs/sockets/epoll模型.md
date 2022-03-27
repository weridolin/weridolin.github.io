## 为什么要有epoll模型？
虽然select模型能够是用户端实现完全的非阻塞，但实际上在内核态依然是对socket列表的遍历轮询(*O(N)*),并且每次调用select时都要传递socket，在高并发下这个开销较大.

## epoll相比select不同的地方
- 内核中保存一份socket list，无需用户每次都重新传入，只需告诉内核修改的部分即可。
- 内核不再通过轮询的方式找到就绪的socket，而是通过异步 IO 事件唤醒。
- 内核仅会将有 IO 事件的socket返回给用户，用户也无需遍历整个文件描述符集合。

## epoll步骤
- 1.创建一个 epoll 句柄
``int epoll_create(int size);``
- 2.向内核添加、修改或删除要监控的socket。
```
int epoll_ctl(
int epfd, 
int op, 
int fd, 
struct epoll_event *event);

```
- 3  类似select()的epoll_wait调用
```
int epoll_wait(
int epfd, 
struct epoll_event *events, 
int max events, 
int timeout);

```

## python epoll
```python

## linux才有 epoll 必须在linux才能运行
import socket, select

EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
response  = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
response += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
response += b'Hello, world!'

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('0.0.0.0', 9527))
serversocket.listen(1)
serversocket.setblocking(0)

epoll = select.epoll()
epoll.register(serversocket.fileno(), select.EPOLLIN) # 注册server socket,监听读取事件（select.EPOLLIN），当有新连接时(握手)，则产生一个读取事件

try:
    connections = {}; requests = {}; responses = {}
    while True:
        events = epoll.poll(1) # 类似select函数，返回这次调用触发的事件列表，列表元素格式为tuple(socket.fd,event)
        # print("<"*30,"调用epoll",">"*30)
        for fileno, event in events:
            if fileno == serversocket.fileno(): # 如果事件对应的socket文件描述符为sever，说明有新连接进来
                connection, address = serversocket.accept() # 完成握手,生成一个socket fd
                connection.setblocking(0)
                epoll.register(connection.fileno(), select.EPOLLIN) # 注册socket-fd到内核,监听读取事件
                print(f">>>register socket:{connection.fileno()}")
                connections[connection.fileno()] = connection
                requests[connection.fileno()] = b''
                responses[connection.fileno()] = response
            elif event == select.EPOLLIN: # 如果事件为读取事件
                requests[fileno] += connections[fileno].recv(1024)
                print(f"get data from socket:{fileno},{requests[fileno]}")
                if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                    epoll.modify(fileno, select.EPOLLOUT) # 读取一个完整的request,以 EOL1和 EOL2 即为
                    print('-'*40 + '\n' + requests[fileno].decode()[:-2])
            elif event == select.EPOLLOUT: # 如果事件为写事件
                byteswritten = connections[fileno].send(responses[fileno])
                print(f"send data to socket:{fileno}:{responses[fileno][:byteswritten]} ")
                responses[fileno] = responses[fileno][byteswritten:]
                if len(responses[fileno]) == 0:
                    epoll.modify(fileno, 0)  # 一旦所有的返回数据都发送完, 取消监听读取和写入事件.
                    connections[fileno].shutdown(socket.SHUT_RDWR) # 关闭连接
            elif event == select.EPOLLHUP:
                # HUP(hang-up)事件表示客户端断开了连接(比如 closed), 所以服务器这端也会断开. 
                # 不需要注册HUP事件, 因为它们都会标示到注册在epoll的socket
                epoll.unregister(fileno)
                connections[fileno].close()
                del connections[fileno]
        # print("<"*30,"结束调用epoll",">"*30)
finally:
    # 异常，注销服务端运行的服务
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()

# 同样运行client.py，服务端输出为:  
# >>>register socket:5
# get data from socket:5,b'client msg:0\n\n'
# ----------------------------------------
# client msg:0
# send data to socket:5:b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, world!' 
# >>>register socket:6
# get data from socket:6,b'client msg:1\n\n'
# ----------------------------------------
# client msg:1
# send data to socket:6:b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, world!' 
# >>>register socket:7
# get data from socket:7,b'client msg:2\n\n'
# ----------------------------------------
# client msg:2
# send data to socket:7:b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, world!' 


```
  
### 具体逻辑
- 1. 与select不同的是,每次调用epoll()时,不用再传递整个*fd list*进去,而是直接调用注册函数，传递要监听的socket，以及监听的事件类型。
- 2. 内核态的epoll方法是通过事件触发来回调的，一旦有事件满足马上返回，返回的类型为 *list[tuple(fd,event)]*