import sys,time
def child():   
    print("child process start")
    while True: 
        str_= sys.stdin.readline()
        print(">>>get std in",str_)
        time.sleep(1)

if __name__ =="__main__":
    child()

