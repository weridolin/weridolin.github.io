## logging 模块几大件

#### filter
logging 模块的过滤列表。*logger*的filter是一个列表,只有要记录的*record*不满足过滤的条件.才会最终被处理.直接看源码
```python
class Filter(object):
    """
    Filter instances are used to perform arbitrary filtering of LogRecords.

    Loggers and Handlers can optionally use Filter instances to filter
    records as desired. The base filter class only allows events which are
    below a certain point in the logger hierarchy. For example, a filter
    initialized with "A.B" will allow events logged by loggers "A.B",
    "A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If
    initialized with the empty string, all events are passed.
    """
    def __init__(self, name=''):
        """
        Initialize a filter.

        Initialize with the name of the logger which, together with its
        children, will have its events allowed through the filter. If no
        name is specified, allow every event.
        """
        self.name = name
        self.nlen = len(name)

    def filter(self, record):
        """
        Determine if the specified record is to be logged.

        Returns True if the record should be logged, or False otherwise.
        If deemed appropriate, the record may be modified in-place.
        """
        if self.nlen == 0:
            return True
        elif self.name == record.name:
            return True
        elif record.name.find(self.name, 0, self.nlen) != 0: # 正常应该从 0 开始
            return False
        return (record.name[self.nlen] == ".")

class Filterer(object):
    """
    A base class for loggers and handlers which allows them to share
    common code.
    """
    def __init__(self):
        """
        Initialize the list of filters to be an empty list.
        """
        self.filters = []

    def addFilter(self, filter):
        """
        Add the specified filter to this handler.
        """
        if not (filter in self.filters):
            self.filters.append(filter)

    def removeFilter(self, filter):
        """
        Remove the specified filter from this handler.
        """
        if filter in self.filters:
            self.filters.remove(filter)

    def filter(self, record):
        """
        Determine if a record is loggable by consulting all the filters.

        The default is to allow the record to be logged; any filter can veto
        this and the record is then dropped. Returns a zero value if a record
        is to be dropped, else non-zero.

        .. versionchanged:: 3.2

            Allow filters to be just callables.
        """
        # 不能被记录即直接过滤掉 
        rv = True
        for f in self.filters:
            if hasattr(f, 'filter'):
                result = f.filter(record)
            else:
                result = f(record) # 
            if not result:
                rv = False
                break
        return rv


```
- 所有*logger*继承于*Filterer*.在调用*handle*方法之前会去调用*logger.filter*方法.*filter*会判断*record*是否满足filter列表的要求.只要有一个*filter*return false.则不会执行这一条record.
- 要自定义*filter*,只需继承于*Filter*，并实现*class.filter* or *class._call_*方法即可.   

自定义filter如下:

```python

import logging
messages = []
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

class ListenFilter(logging.Filter):

    def filter(self, record):
        """Determine which log records to output.Returns 0 for no, nonzero for yes.
        """
        if record.getMessage().startswith('i am filter'): ## 过滤掉 i am filter 开头的日志
            return False # 只要filter列表有一个返回False.该条record就被过滤掉
        return True
_filter = ListenFilter()
logger.addFilter(filter=_filter)
logger.debug("i am filter >>>>")
logger.debug("i am not filter >>>>")

# >>>>> i am not filter 
```

#### handler
*handler*为*logger*中实际对*record*的处理。*logger*的logger是一个列表,只有要记录的*record*不被过滤,最终会被handle列表中的每个handle处理.直接看源码
```python
### logging handler 基类

class Handler(Filterer):
    """
    Handler instances dispatch logging events to specific destinations.

    The base handler class. Acts as a placeholder which defines the Handler
    interface. Handlers can optionally use Formatter instances to format
    records as desired. By default, no formatter is specified; in this case,
    the 'raw' message as determined by record.message is logged.
    """
    def __init__(self, level=NOTSET):
        """
        Initializes the instance - basically setting the formatter to None
        and the filter list to empty.
        """
        Filterer.__init__(self)
        self._name = None
        self.level = _checkLevel(level)
        self.formatter = None
        # Add the handler to the global _handlerList (for cleanup on shutdown)
        _addHandlerRef(self)
        self.createLock()

    ...

    def emit(self, record):
        """
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        """
        raise NotImplementedError('emit must be implemented '
                                  'by Handler subclasses')

    def handle(self, record):
        """
        Conditionally emit the specified logging record.

        Emission depends on filters which may have been added to the handler.
        Wrap the actual emission of the record with acquisition/release of
        the I/O thread lock. Returns whether the filter passed the record for
        emission.
        """
        rv = self.filter(record)
        if rv:
            self.acquire()
            try:
                self.emit(record)
            finally:
                self.release()
        return rv

    def setFormatter(self, fmt):
        """
        Set the formatter for this handler.
        """
        self.formatter = fmt

    def flush(self):
        """
        Ensure all logging output has been flushed.

        This version does nothing and is intended to be implemented by
        subclasses.
        """
        pass

    def close(self):
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        _handlers, which is used for handler lookup by name. Subclasses
        should ensure that this gets called from overridden close()
        methods.
        """
        #get the module data lock, as we're updating a shared structure.
        _acquireLock()
        try:    #unlikely to raise an exception, but you never know...
            if self._name and self._name in _handlers:
                del _handlers[self._name]
        finally:
            _releaseLock()

    def handleError(self, record):
        """
        Handle errors which occur during an emit() call.

        This method should be called from handlers when an exception is
        encountered during an emit() call. If raiseExceptions is false,
        exceptions get silently ignored. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        """
        if raiseExceptions and sys.stderr:  # see issue 13807
            t, v, tb = sys.exc_info()
            try:
                sys.stderr.write('--- Logging error ---\n')
                traceback.print_exception(t, v, tb, None, sys.stderr)
                sys.stderr.write('Call stack:\n')
                # Walk the stack frame up until we're out of logging,
                # so as to print the calling context.
                frame = tb.tb_frame
                while (frame and os.path.dirname(frame.f_code.co_filename) ==
                       __path__[0]):
                    frame = frame.f_back
                if frame:
                    traceback.print_stack(frame, file=sys.stderr)
                else:
                    # couldn't find the right stack frame, for some reason
                    sys.stderr.write('Logged from file %s, line %s\n' % (
                                     record.filename, record.lineno))
                # Issue 18671: output logging message and arguments
                try:
                    sys.stderr.write('Message: %r\n'
                                     'Arguments: %s\n' % (record.msg,
                                                          record.args))
                except RecursionError:  # See issue 36272
                    raise
                except Exception:
                    sys.stderr.write('Unable to print the message and arguments'
                                     ' - possible formatting error.\nUse the'
                                     ' traceback above to help find the error.\n'
                                    )
            except OSError: #pragma: no cover
                pass    # see issue 5971
            finally:
                del t, v, tb

    def __repr__(self):
        level = getLevelName(self.level)
        return '<%s (%s)>' % (self.__class__.__name__, level)

    ### 

```
- 默认的handler是先进行*filter*过滤，如果不满足过滤的条件。则调用*emit*进行
- 自定义*handler*只需要实现了*emit*方法即可。
- 一个自定义的*handler*如下
```python


import logging
messages = []
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RequestsHandler(logging.Handler):
    def emit(self, record):
        """Send the log records (created by loggers) to
        the appropriate destination.
        """
        print("deal message",record.getMessage())
        messages.append(record.getMessage())

handler = RequestsHandler()
logger.addHandler(handler) # 只需要定义一个handler并添加到logger即可

logger.info(">>> iiiiiiiiii")

>>>  deal message >>> iiiiiiiiii

```
#####  自定义一个循环文件logging handler

继承于*BaseRotatingHandler*,实现*doRollover*，*shouldRollover*即可

```python
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

```


#### logger
*logger*代表了一个实际的日志处理器.每次调用logger.实际上都是初始化了一个*logger*实例,*logger*需要添加对应的*handler*和*filter*,每个*logger*都是以名字作为唯一标识 

```python
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

```

#### LoggerAdapter
LoggerAdapter是logging自带的一个*logger*的一个适配器。主要是在调用*log*前引入了*process*的处理过程,直接看源码       

```python
class LoggerAdapter(object):
    """
    An adapter for loggers which makes it easier to specify contextual
    information in logging output.
    """

    def __init__(self, logger, extra):
        """
        Initialize the adapter with a logger and a dict-like object which
        provides contextual information. This constructor signature allows
        easy stacking of LoggerAdapters, if so desired.

        You can effectively pass keyword arguments as shown in the
        following example:

        adapter = LoggerAdapter(someLogger, dict(p1=v1, p2="v2"))
        """
        self.logger = logger
        self.extra = extra

    def process(self, msg, kwargs):
        """
        Process the logging message and keyword arguments passed in to
        a logging call to insert contextual information. You can either
        manipulate the message itself, the keyword args or both. Return
        the message and kwargs modified (or not) to suit your needs.

        Normally, you'll only need to override this one method in a
        LoggerAdapter subclass for your specific needs.
        """
        kwargs["extra"] = self.extra
        return msg, kwargs

        ...

    def log(self, level, msg, *args, **kwargs):
        """
        Delegate a log call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs) ## 调用 log 前会进行*process*预处理
            self.logger.log(level, msg, *args, **kwargs)


    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        """
        Low-level log implementation, proxied to allow nested logger adapters.
        """
        return self.logger._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=extra,
            stack_info=stack_info,
        )

```
- 通过*LoggerAdapter*，可以实现一个简单的*logging*的拦截器。即只需要继承*LoggerAdapter*，实现*logger.process*即可

```python

from logging import LoggerAdapter

class LoggerInterceptor(LoggerAdapter):

    def process(self, msg, kwargs):
        msg = str(msg)+"i am interceptor"
        return super().process(msg, kwargs)

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())
logger = LoggerInterceptor(logger=_logger,extra={"extra_option":"Var1"})

logger.info(">>>>>>>") # >>> >>>>>>>i am interceptor

```