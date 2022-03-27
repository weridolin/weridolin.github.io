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
                    s.send(b"hello")
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
# 由上可见，对多个socket连接的监听和处理可以简化为一个线程，并且在用户态优化成非阻塞状态，剩下的交给内核态select去处理
# 用户态只需要不断去调用 select，每次去对应获取要处理的socket列表即可