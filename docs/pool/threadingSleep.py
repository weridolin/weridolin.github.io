import threading,time


class SleepThread(threading.Thread):
    
    exit_flag = False

    def run(self) -> None:
        ## 把sleep拆成多个小间隔的sleep
        for _ in range(1000):
            # sleep过程中响应对应的逻辑操作
            if self.exit_flag:
                print("exit")
                break
            time.sleep(0.1)
        return super().run()

class SleepThread(threading.Thread):
    
    exit_flag = threading.Event()

    def run(self) -> None:
        ## 把sleep拆成多个小间隔的sleep
        self.exit_flag.wait(100)
        print("exit")
        return super().run()



if __name__ =="__main__":
    # t = SleepThread()
    # t.start()
    # time.sleep(2)
    # t.exit_flag=True # 自定义退出标记
    # t.exit_flag.set() # 利用 threading.Event()的set来退出
    # t.join()
    # main = threading.main_thread()
    ...
    
