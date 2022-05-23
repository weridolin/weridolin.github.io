# from asyncio.subprocess import PIPE
# import subprocess,sys,os,time
# if __name__ =="__main__":
#     child_file = os.path.join(os.path.dirname(__file__),"child.py")
#     child_p = subprocess.Popen(
#         args=[sys.executable,child_file],
#         # stdin=subprocess.PIPE
#         stdout=subprocess.PIPE
#     )
#     # for _ in range(10):
#     #     child_p.stdin.write(f"write data:{_}\r\n".encode())
#     #     child_p.stdin.flush()
#     # while True:
#     #     time.sleep(1)
#     while child_p.poll() is None:
#         output = child_p.stdout.readline()
#         print(">>> get child output",output)

from concurrent.futures import ProcessPoolExecutor
import os
import time
def child_process(index):
    # while True:
    print(f">>> child process --> id :{os.getpid()},index:{index}" )
    # return os.getpid()
    time.sleep(4)

def finish_callback(future):
    print(future.result())


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=2) as executor:
        for i in range(4):
            t = executor.submit(child_process,index=1)
            # t.add_done_callback(finish_callback)

        time.sleep(9)