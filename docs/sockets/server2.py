import socket,threading


def handle_data(conn,addr):
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            if not data: break
            conn.sendall(data)
            print(f"reply data:{data},index:{conn_list.index((conn,addr))}".encode("utf-8"))

HOST = '0.0.0.0'                 # Symbolic name meaning all available interfaces
PORT = 50007  
conn_list = []            # Arbitrary non-privileged port
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept() # 第一步阻塞，接收到链接，返回conn,和链接地址
        conn_list.append((conn,addr))
        print(f"接收到新连接:{conn},{addr}")
        t = threading.Thread(target=handle_data,args=(conn,addr),daemon=False)
        t.start()



