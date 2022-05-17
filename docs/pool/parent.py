from asyncio.subprocess import PIPE
import subprocess,sys,os,time
if __name__ =="__main__":
    child_file = os.path.join(os.path.dirname(__file__),"child.py")
    child_p = subprocess.Popen(
        args=[sys.executable,child_file],
        # stdin=subprocess.PIPE
        stdout=subprocess.PIPE
    )
    # for _ in range(10):
    #     child_p.stdin.write(f"write data:{_}\r\n".encode())
    #     child_p.stdin.flush()
    # while True:
    #     time.sleep(1)
    while child_p.poll() is None:
        output = child_p.stdout.readline()
        print(">>> get child output",output)
    