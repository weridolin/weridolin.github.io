"""
    按照日志内容行数切割

    example:
        from line_cutter import FileLineRotatingHandler
        import logging
        logger = logging.getLogger(__file__)
        # Add the log message handler to the logger
        handler = FileLineRotatingHandler("test.log.0", maxline = 10)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        for i in range(40):
            logger.info(f">>>> {i}")    
"""
from  logging.handlers import BaseRotatingHandler
import os
class FileLineRotatingHandler(BaseRotatingHandler):

    def __init__(self, filename, mode: str="a+", encoding =None, delay: bool=None,errors =None,maxline = 100,backupCount=None) -> None:
        ### 文件按100行去切割，backupCount为保存的最大文件个数
        super().__init__(filename, mode, encoding, delay, errors)
        self.maxline = maxline
        self.backupCount = backupCount
        if self.backupCount and self.backupCount < 1:
            raise ValueError("backup count can not < 1")

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount and self.backupCount > 0:
            # 限定最大文件切割个数
            for i in range(int(self.backupCount-1),0,-1):
                ## 把已经有的历史记录 + 1 todo backupCount limit
                sfn = self.rotation_filename(self.baseFilename.replace("0",str(i)))
                dfn = self.rotation_filename(self.baseFilename.replace("0",str(i + 1)))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)            
        else:
            # 否则则不断累加
            already_file_count = self.get_file_count()
            for i in range(int(already_file_count),0,-1):
                ## 把已经有的历史记录 + 1 todo backupCount limit
                sfn = self.rotation_filename(self.baseFilename.replace("0",str(i)))
                dfn = self.rotation_filename(self.baseFilename.replace("0",str(i + 1)))
                # print(dfn,sfn)
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            # 当前写的文件 更新为 log.1 baseFilename:log.0
        dfn = self.rotation_filename(self.baseFilename.replace("0","1"))
        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if not self.delay:
            # 新建一个新的 log.0
            self.stream = self._open()

    def shouldRollover(self, record):
        if self.stream is None:              
            self.stream = self._open()
        if self.maxline > 0:                   
            self.stream.seek(0,0)
            num_lines = len(self.stream.readlines()) 
            if self.maxline >= num_lines + 1:
                return 0
        return 1

    def get_file_count(self):
        _dir = os.path.dirname(self.baseFilename)
        file_list = [file for file in os.listdir(_dir) if "log" in file and "log.0" not in file]
        if file_list:
            latest_file  = sorted(file_list,key = lambda file:int(file.split(".")[-1]))[-1]
            count  = latest_file.split(".")[-1]
            return count if not isinstance(count,int) else count
        else:
            return 0