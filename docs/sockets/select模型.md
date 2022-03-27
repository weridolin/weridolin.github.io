## select模型
由普通IO的阻塞模型原理可知，要想进一步提高并发能力，缓解I/O阻塞的影响，不能单单停留在用户态的改进（多线程/线程池）, 最好是直接内核方法 accept 和 recv 的调用直接做成非阻塞，这里就引入了select模型。        

select也是内核态的一个方法，但他是非阻塞的，方法和参数如下：
```C
int select(
    int maxfdp1, ### 最大的文件描述监听数
    fd_set *readset,  ## 监听的文件集合
    fd_set *writeset, 
    fd_set *exceptset, ### 分别指向可读、可写和异常等事件对应的打开的文件描述符集合。
    const struct timeval *timeout); ## 用于设置select函数的超时时间，即告诉内核select等待多长时间之后就放弃等待。timeout == NULL 表示等待无限长的时间

```
返回值：符合传入的fd_Set状态的格式，PYTHON里面返回的为符合入参状态的*readable/writable/exceptable*的列表，分别为各个入参的子集

## 与传统的阻塞socket改进的地方
传统的阻塞方式是方式：用户态有2个阻塞的地方，1个是accept()新的链接，一个是recv()数据，而select主要是改进了recv()方式。之前最好的方式是每个链接用一个线程去recv()数据(哪怕是非阻塞状态，也是循环不断去轮询recv()),这样一个会很消耗线程，另外一个每个线程都要去调用内核态的recv()方法。   
采用select，调用所有文件会被添加到一个list里面并传送给内核态，用户态只需要用一个线程每次去调用select,内核态遍历传进来的socket 列表，如果有准备就绪的数据，则添加对应的标记，并返回对应就绪的文件数给到用户态，用户再去遍历这个文件列表，找出就绪的socket连接。  

## 主要几个逻辑
- 所有的新建链接会被添加一个socket file list的列表。
- 循环调用内核态select()方法，调用时会把整个socket file list传进去
- 内核态遍历socket file list，如果有可读状态(接收到数据)，则返回对应的可执行数
- 用户态遍历 socket file list，处理对应的就绪的file


## 例子
- 1.服务端接收客户端连接，并接受客户端发送数据

```python
#### SELECT 例子 python 
import select, socket, sys,time
import queue
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0) # 设置为非阻塞
server.bind(('localhost', 9527))
server.listen(5)
inputs = [server]
outputs = []
client_list={}

while inputs:
    # 调用一个内核 select 方法，返回可读/可写/异常的文件描述符列表
    # 参数：1.需要检验是否为输入状态的socket 列表，是否为可写状态的输出socket 列表,是否为异常的socket 列表
    # 返回的三个列表为对应的输入的子集
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    print(f"select return list >> readable:{readable},\nwritable:{writable},\nexception:{exceptional}")
    for s in readable:
        if s is server:
            # server 描述符为可读状态，说明已经新的客户端已经发送握手请求
            connection, client_address = s.accept()
            connection.setblocking(0)
            inputs.append(connection) # 建立连接，新的SOCKET添加到inputs
    time.sleep(1)
    print(f"now socket list >> input:{inputs},\noutput:{outputs},\nexception:{exceptional}")

## 输出
# now socket list >> input:[<socket.socket fd=304, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527)>, <socket.socket fd=428, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60095)>, <socket.socket fd=444, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60094)>, <socket.socket fd=440, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60096)>], ## 3个客户端完成握手过程后，需要轮询的socket个数增加到4个
# output:[],
# exception:[]
# select return list >> readable:[<socket.socket fd=428, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60095)>, <socket.socket fd=444, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60094)>, <socket.socket fd=440, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 9527), raddr=('127.0.0.1', 60096)>],## select返回的3个处于readable状态的3个socket，因为没有新的连接请求，返回的readable列表不包括server


```
我们同样利用[client.py](client.py)去模拟三个请求，那么我们会看到,经过三次select调用后，能够完全捕获到新建立的3个连接请求().第一次调用的时候，*input*只有*server*一个套接字,调用后*server*进入*readable*状态，即为收到客户端的握手请求.调用*accept*后完成握手，返回一个新的socket套接字,同时添加到*input*，同时下次调用*select*时再传入该*input*,返回时再重复去处理*readable*列表,最终*inputs*列表有4个socket套接字，包括1个server3个client，返回的*readable*列表为传入的*3个client*(client已经发送数据到服务端)

- 服务端读取客户端发送的数据
我们再给上述代码加上读取客户端数据的逻辑
```python
while inputs:
    # 调用一个内核 select 方法，返回可读/可写/异常的文件描述符列表
    # 参数：1.需要检验是否为输入状态的socket 列表，是否为可写状态的输出socket 列表,是否为异常的socket 列表
    # 返回的三个列表为对应的输入的子集
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    print(f"select return list >> readable:{readable},\nwritable:{writable},\nexception:{exceptional}")
    for s in readable:
        if s is server:
            # server 描述符为可读状态，说明已经新的客户端已经发送握手请求
            connection, client_address = s.accept()
            connection.setblocking(0)
            inputs.append(connection) # 建立连接，新的SOCKET添加到inputs
        else:
            data = s.recv(1024)
            if data:
                print(f"socket:{s} get data{data}")
                if s not in outputs:
                    outputs.append(s) # 进入需要检验为是否可写，下次调用select 传入
    time.sleep(1)

```
上述代码在第一步的前提下，加入的对readable状态socket数据的读取(非server)，读取后该socket的状态不再为*readable*,这里要注意也不是就是*writable*状态，判断是不是*readable*或者*writable*状态都要通过内核方法*select*返回的socket列表来确定。在用户态，需要更改的是传入的 *inputs*列表(判断是否可读),*outputs*列表(判断是否可写).上述对*readable*状态列表的读取数据后，要做出回复，所以要把需要回复的*socket*添加到*outputs*列表(判断是否可写)中，通过下次调用select函数来返回的*writable*列表是否为可写。也可以收到数据后，直接调用*send*方法发送数据

- 服务端回复客户端的数据
这里是通过select来返回可写的socket列表，也可以对readable socket 读取数据的时候直接做出回复，可以减少内核再去对socket列表遍历
```python

#### SELECT 例子
import select, socket, sys,time
import queue
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0) # 设置为非阻塞
server.bind(('localhost', 9527))
server.listen(5)
inputs = [server]
outputs = []
msg_cache={}

while inputs:
    # 调用一个内核 select 方法，返回可读/可写/异常的文件描述符列表
    # 参数：1.需要检验是否为输入状态的socket 列表，是否为可写状态的输出socket 列表,是否为异常的socket 列表
    # 返回的三个列表为对应的输入的子集
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    # print(f"select return list >> readable:{readable},\nwritable:{writable},\nexception:{exceptional}")
    for s in readable:
        if s is server:
            # server 描述符为可读状态，说明已经新的客户端已经发送握手请求
            connection, client_address = s.accept()
            connection.setblocking(0)
            inputs.append(connection) # 建立连接，新的SOCKET添加到inputs
            # 添加消息缓存队列
            msg_cache[connection.fileno()] = queue.Queue()
        else:
            data = s.recv(1024).decode("utf-8")
            if data:
                print(f"socket:{s.fileno()} get data:{data}")
                if "close" in data:
                    print(f"close socket:{s.fileno()}")
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    msg_cache.pop(s.fileno())
                    s.close()
                    # print(msg_cache)
                else:
                    if s not in outputs:
                        outputs.append(s) # 进入需要检验为是否可写，下次调用select 传入
                    # if s in  inputs:
                    msg_cache[connection.fileno()].put(data)
    time.sleep(1)
    for s in writable:
        # print(msg_cache)
        try:
            msg = msg_cache[s.fileno()].get_nowait()
        except queue.Empty:
            outputs.remove(s) # 下次调用select只需校验是否为可读状态
        except KeyError:
            pass
        else:
            if not s._closed:
                s.send(f"get message:{msg}".encode("utf-8"))
    time.sleep(1)
    # for s in exceptional:
    #     inputs.remove(s)
    #     if s in outputs:
    #         outputs.remove(s)
    #     s.close()
    print(f"now socket list >> input:{inputs},\noutput:{outputs},\nexception:{exceptional}")

```
由上可见，对多个socket连接的监听和处理可以简化为一个线程，并且在用户态层级优化成非阻塞状态，剩下的交给内核态select去处理，用户态只需要不断去调用 select，每次去对应获取要处理的socket列表即可。多个socket只有一次 select 的系统调用 + n 次就绪状态的文件描述符的 read 系统调用

## select的缺点
- 单个进程所打开的FD是有限制的，通过FD_SETSIZE设置，默认1024（*poll模型无限制，其他同select大致相同*）
- 每次调用select，都需要把fd集合从用户态拷贝到内核态，这个开销在fd很多时会很大
- 对socket扫描时是线性扫描，采用轮询的方法，效率较低（高并发时）

## TODO SELECT内核实现
