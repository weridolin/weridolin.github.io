## 什么是gevent？
在python自带的异步模块asynico出来之前,gevent是一个支持协程的python库,其基于**libev**or**libuv**实现了python的协程.gevent将python的一些I/O内置库,比如socket/select/threading/subprocess等.每一个I/O操作会被封装成一个支持的异步的greenlet(相当于asyncio的task),然后自身实现的事件循环loop进行驱动


## monkey patch
在异步模块asynico出来之前,由于python内置的I/O库无法支持异步，所以gevent自身把python相关的网络库改写成了支持的异步,使用了monkey patch后,import相关的库实际上会import了gevent改写后的对应的库.


## event_loop/hub 
gevent的event_loop是基于**libev**和**libuv**来写的.每个event-loop会被封装到Hub里面，每一个线程拥有唯一的一个HUB实例(这点和python自带的asyncio-eventloop相似).Hub可以当成一个特殊的**greenlet**,专门用来运行对应的事件循环**event-loop**.当有greenlet任务提交时,会自动调用**HUB().loop.run()**,不断去轮询对应的I/O事件，直至所有的greenlet执行完毕，eventloop抛出异常。**hub**在这里可以理解为一个命名空间?表示当前线程所在event-loop的一个运行空间(个人理解- -)

### spawn/spawn_later
- spawn类似于asyncio-event-loop对应call_soon,主要是把greenlet添加event-loop执行列表里面，下次执行时立马调用.即当前如果有其他的greenlet在执行,则在遇到I/O挂起后,继续获取下个greenlet时作为下一个greenlet去执行.
- spawn_later相当于类似于asyncio-event-loop对应call_later,即greenlet延时一定时间才添加到event-loop待执行的greenlet列表里面

## greenlet
greenlet是gevent里面的执行对象，相当于asyncio的task. greenlet的封装和task很相似,这里简单总结一下:       

| gevent-greenlet  | asyncio-task   |   说明          | 
| -----------       | -----------   |-----------     |
| instance.run     |  instance._core              | 实际执行的协程函数                |
| instance.kill()     |  instance.cancel()              | 取消改协程的执行            |
| instance.spawn()/start()     |  instance.cancel()              | 创建一个协程,并通过Hub()添加到event-loop的执行任务中 |
| instance.spawn_later()/start_later()   |  instance.cancel()  | 创建一个协程,并在N秒后通过Hub()添加到event-loop的执行任务中|
| instance.add_spawn_callback   |    | 协程开始执行后的回调|
| instance.rawlink()/link_value()/link_exception()   |    | 协程执行完成后的回调的回调/执行成功后才回调/失败后才回调|
| instance.join()     |  instance.cancel()              | 等到改greentLet执行完成     |
| instance.switch()     |  instance.cancel()              | 等到改greentLet执行完成     |