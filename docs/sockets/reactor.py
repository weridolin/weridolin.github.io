import socket,select
from http import server
import time,os
from concurrent.futures import ThreadPoolExecutor,Future


class SingleProcessSingleThreadReactor:

    handle_map = dict()

    def __init__(self) -> None:
        self.inputs=list()
        self.outputs = list()
        self.exceptions= list()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0) # 设置为非阻塞
        self.server.bind(('0.0.0.0', 8888))
        self.register_self()
    
    def register_self(self):
        self.register_fd(
            self.server,Acceptor(self)
        )


    def run_forever(self):
        self.server.listen() # backlog，指定半链接队列的最大长度
        while self.inputs:
            if len(self.inputs) > 512:  # windows系统下select的最大fd个数为512
                if len(self.inputs) % 512==0 :
                    loop_count = int(len(self.inputs)/512) 
                else:
                    loop_count = int(len(self.inputs)/512) + 1
            else:
                loop_count = 1
            for i in range(loop_count):
                try:
                    _inputs = self.inputs[i*512:i*512+512] if i!= loop_count-1 else  self.inputs[i*512:]
                    readable, writable, exceptional = select.select(
                        _inputs,
                        self.outputs, 
                        _inputs+self.outputs) # 
                    print(f"select result --> \n inputs sockets:{readable}. \n outputs sockets:{writable} \n. exceptions sockets:{exceptional}")

                    self.dispatch(readable,writable,exceptional)
                except InterruptedError:
                    break
                except Exception as exc:
                    raise

    def dispatch(self,read_fds,write_fds,exceptions_fds):
        for fd in read_fds:
            handler = self.handle_map.get(fd.fileno())
            handler.handle(fd)

        for fd in write_fds:
            ...

        for fd in exceptions_fds:
            ...

    def register_fd(self,fd,handler):
        if len(self.inputs)> 1024:
            raise ValueError("SELECT 一次性监听的fd个数不能超过1024")
        if not isinstance(fd,int):
            file_no = fd.fileno()
        else:
            file_no = fd
        self.handle_map.update({
            file_no:handler
        })
        self.inputs.append(fd)


    def remove_fd(self,fd):
        if not isinstance(fd,int):
            file_no = fd.fileno()
        else:
            file_no = fd
        if file_no in self.handle_map:
            self.handle_map.pop(file_no)
        if fd in self.inputs:
            self.inputs.remove(fd)
        if fd in self.outputs:
            self.outputs.remove(fd)


class Handler:
    
    __instance = None

    def __new__(cls,*args,**kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self,reactor=None) -> None:
        self.reactor:SingleProcessSingleThreadReactor = reactor

    def handle(self,sock):
        try:
            data = sock.recv(1024).decode("utf-8")
            if len(data)==0: 
                # 当 socket 的一段关闭时,调用 sock.recv ,会一直收到 O字节的数据 
                # @https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recv
                print(f"socket client:{sock} has closed")
                self.reactor.remove_fd(sock)
            else:
                print(f"socket:{sock} get data:{data}")
                sock.sendall("hello word".encode("utf-8"))

        except ConnectionResetError:
            print(f"socket client:{sock} has close force")
            sock.close()
            self.reactor.remove_fd(sock)


class Acceptor(Handler):

    def handle(self, sock):
        print("before socket accept")
        new_con,addr = sock.accept()
        new_con.setblocking(False)
        print(f"accept a new sock connection:{addr}")
        self.reactor.register_fd(new_con,Handler(reactor=self.reactor))


class SingleProcessMultipleThreadsReactor(SingleProcessSingleThreadReactor):

    def __init__(self,max_worker = None) -> None:
        self._executor = ThreadPoolExecutor(max_workers=os.cpu_count() + 4 or max_worker)
        super().__init__()


    def register_self(self):
        self.register_fd(
            self.server,SingleProcessMultipleThreadsAcceptor(self)
        )


class SingleProcessMultipleThreadsHandler(Handler):
    
    def handle(self, sock):
        try:
            data = sock.recv(1024).decode("utf-8")
            if len(data)==0: 
                # 当 socket 的一段关闭时,调用 sock.recv ,会一直收到 O字节的数据 
                # @https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recv
                print(f"socket client:{sock} has closed")
                self.reactor.remove_fd(sock)
            else:
                print(f"socket:{sock} get data:{data}")
                # sock.sendall("hello word".encode("utf-8"))
                assert isinstance(self.reactor,SingleProcessMultipleThreadsReactor)
                fut = self.reactor._executor.submit(
                    self.mock_deal_data_in_thread,data,sock
                )
                fut.add_done_callback(self.finish)

        except ConnectionResetError:
            print(f"socket client:{sock} has close force")
            sock.close()
            self.reactor.remove_fd(sock)
        

    def mock_deal_data_in_thread(self,data,sock):
        print(f"mock deal data:{data}")
        time.sleep(1)
        return sock
    
    def finish(self,fut:Future):
        sock = fut.result()
        sock.sendall("deal finish".encode("utf-8"))



class SingleProcessMultipleThreadsAcceptor(SingleProcessMultipleThreadsHandler):

    def handle(self, sock):
        print("before socket accept")
        new_con,addr = sock.accept()
        new_con.setblocking(False)
        print(f"accept a new sock connection:{addr}")
        self.reactor.register_fd(new_con,SingleProcessMultipleThreadsHandler(reactor=self.reactor))


if __name__ =="__main__":
    # rs = SingleProcessSingleThreadReactor()
    rs = SingleProcessMultipleThreadsReactor()
    rs.run_forever()
