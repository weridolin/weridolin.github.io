import socket
import threading
import time
def build_client(index):
    HOST = '127.0.0.1'    # The remote host
    PORT = 50007              # The same port as used by the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        time.sleep(3)
        msg = f"client msg:{index}"
        s.sendall(msg.encode("utf-8"))
        while True:
            try:
                data = s.recv(1024)
                print('Received', repr(data))
                time.sleep(3)
            except:
                break
            time.sleep(1)

# for i in range(3):
#     t = threading.Thread(target=build_client,args=(i,),daemon=False)
#     t.start()

build_client(1)