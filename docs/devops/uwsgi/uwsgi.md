## 什么是uwsgi
uwsgi可以理解为一个高性能的HTTP服务器,其实现了[WSGI协议](../../WSGI/1-python%E5%8E%9F%E7%94%9F%E7%9A%84wsgi%E6%A8%A1%E5%9D%97.md),可以兼容*Flask*,*django*等遵循WSGI协议的WEB框架.

## uwsgi充当的角色
一个遵循WSGI协议的请求流程为:       
```

-----------                ---------------          --------------- 
 client        -->>>>>>       httpServer    (wsgi)   (DJANGO/flask)
-----------                --------------           --------------


```
而DJANGP/FLASK自带的httpServer并发行是很弱,UWSGI取代的正式httpServer这一部分.


## uwsgi 配置文件
```yaml



```
