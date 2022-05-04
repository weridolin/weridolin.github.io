# selectors
对windows I/O底层接口的封装.对[select模块](../../sockets/select%E6%A8%A1%E5%9E%8B.md)的封装,select是一种socket I/O模型,即将需要监听的I/O列表传给系统内核,内核返回可读/可写/异常I/O三个socket子列表.


## i/o事件
* 1. EVENT_READ:当前监听的文件处于可读状态
* 2. EVENT_WRITE：当前监听的文件处于可写状态

## 使用(参考官方文档例子)
```python

import selectors
import socket

sel = selectors.DefaultSelector()

def accept(sock, mask): # 接收连接，socket i/o 状态变成 EVENT_READ
    conn, addr = sock.accept()  # Should be ready
    print('accepted', conn, 'from', addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, read)

def read(conn, mask): # 客户端发送数据时，socket i/o 状态变成 EVENT_READ
    data = conn.recv(1000)  # Should be ready
    if data:
        print('echoing', repr(data), 'to', conn)
        conn.send(data)  # Hope it won't block
    else:
        print('closing', conn)
        sel.unregister(conn)
        conn.close()

sock = socket.socket()
sock.bind(('localhost', 1234))
sock.listen(100)
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, accept) # 注册socket IO 和回调 data参数可以传一个回调函数

while True:
    events = sel.select()
    for key, mask in events:
        callback = key.data ## key.DATA 就是register时传进入的， mask是对应的event
        callback(key.fileobj, mask)


```

## 源码注释
直接拿SELECT I/O模型来分析,查看注释
```python

class _BaseSelectorImpl(BaseSelector):
    """Base selector implementation."""

    def __init__(self):
        # this maps file descriptors to keys
        self._fd_to_key = {}
        # read-only mapping returned by get_map()
        self._map = _SelectorMapping(self)

    def _fileobj_lookup(self, fileobj): # 返回socket描述符,在windows下即为句柄
        """Return a file descriptor from a file object.

        This wraps _fileobj_to_fd() to do an exhaustive search in case
        the object is invalid but we still have it in our map.  This
        is used by unregister() so we can unregister an object that
        was previously registered even if it is closed.  It is also
        used by _SelectorMapping.
        """
        try:
            return _fileobj_to_fd(fileobj)
        except ValueError:
            # Do an exhaustive search.
            for key in self._fd_to_key.values():
                if key.fileobj is fileobj:
                    return key.fd
            # Raise ValueError after all.
            raise

    def register(self, fileobj, events, data=None):
        if (not events) or (events & ~(EVENT_READ | EVENT_WRITE)):
            raise ValueError("Invalid events: {!r}".format(events))

        # 将要监听的socket文件描述符,监听的文件状态.回调等封装
        key = SelectorKey(fileobj, self._fileobj_lookup(fileobj), events, data) 

        if key.fd in self._fd_to_key:
            raise KeyError("{!r} (FD {}) is already registered"
                           .format(fileobj, key.fd))

        self._fd_to_key[key.fd] = key
        return key

    def unregister(self, fileobj):
        try:
            key = self._fd_to_key.pop(self._fileobj_lookup(fileobj))
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        return key

    def modify(self, fileobj, events, data=None):
        try:
            key = self._fd_to_key[self._fileobj_lookup(fileobj)]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        if events != key.events:
            self.unregister(fileobj)
            key = self.register(fileobj, events, data)
        elif data != key.data:
            # Use a shortcut to update the data.
            key = key._replace(data=data)
            self._fd_to_key[key.fd] = key
        return key

    def close(self):
        self._fd_to_key.clear()
        self._map = None

    def get_map(self):
        return self._map

    def _key_from_fd(self, fd):
        """Return the key associated to a given file descriptor.

        Parameters:
        fd -- file descriptor

        Returns:
        corresponding key, or None if not found
        """
        try:
            return self._fd_to_key[fd]
        except KeyError:
            return None



class SelectSelector(_BaseSelectorImpl):

    """Select-based selector."""

    def __init__(self):
        super().__init__()
        self._readers = set()  ## reader相当于inputs.即监听可读状态的套接字列表
        self._writers = set()  ## writers相当于outputs.即监听可写状态的套接字列表

    def register(self, fileobj, events, data=None):
        key = super().register(fileobj, events, data) # 
        if events & EVENT_READ: 
            self._readers.add(key.fd)
        if events & EVENT_WRITE:
            self._writers.add(key.fd)
        return key

    def unregister(self, fileobj):
        key = super().unregister(fileobj)
        self._readers.discard(key.fd)
        self._writers.discard(key.fd)
        return key

    if sys.platform == 'win32':
        def _select(self, r, w, _, timeout=None):
            r, w, x = select.select(r, w, w, timeout) # 调用内核select
            return r, w + x, []
    else:
        _select = select.select

    def select(self, timeout=None):
        timeout = None if timeout is None else max(timeout, 0)
        ready = []
        try:
            # 每次调用返回readable和writable的socket列表
            r, w, _ = self._select(self._readers, self._writers, [], timeout) 
        except InterruptedError:
            return ready
        r = set(r)
        w = set(w)
        for fd in r | w:
            events = 0
            if fd in r:
                events |= EVENT_READ # 1
            if fd in w:
                events |= EVENT_WRITE # 2

            key = self._key_from_fd(fd)
            if key:
                ready.append((key, events & key.events))
        return ready

```
跟直接调用select不同,selector封装了每个socket要监听的状态以及对应的回调,对系统内核select调用后返回的结果也多了一层封装