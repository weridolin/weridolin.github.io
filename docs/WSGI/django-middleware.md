## 关于django的中间件调用机制
在了解了[WSGI的中间件处理逻辑](./3-WSGI-middleware.md)后,我们再来了解下django自带的中间件生效方式以及是如何实现一个链式调用的结果


## django自带的中间件混合类**MiddlewareMixin**
django的自定义中间件编写规则是继承自带的**MiddlewareMixin**,并具体实现**process_request**,**process_response**,**process_exception**等方法,我们先来看下**MiddlewareMixin**的源码

```python
class MiddlewareMixin:
    sync_capable = True
    async_capable = True

    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response):
    def __init__(self, get_response=None):
        self._get_response_none_deprecation(get_response)
        self.get_response = get_response
        self._async_check()
        super().__init__()

    def _async_check(self):
        """
        If get_response is a coroutine function, turns us into async mode so
        a thread is not consumed during a whole request.
        """
        if asyncio.iscoroutinefunction(self.get_response):
            # Mark the class as async-capable, but do the actual switch
            # inside __call__ to avoid swapping out dunder methods
            self._is_coroutine = asyncio.coroutines._is_coroutine

    def __call__(self, request):
        # Exit out to async mode, if needed
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        response = response or self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response

    async def __acall__(self, request):
        """
        Async version of __call__ that is swapped in when an async request
        is running.
        """
        response = None
        if hasattr(self, 'process_request'):
            response = await sync_to_async(
                self.process_request,
                thread_sensitive=True,
            )(request)
        response = response or await self.get_response(request)
        if hasattr(self, 'process_response'):
            response = await sync_to_async(
                self.process_response,
                thread_sensitive=True,
            )(request, response)
        return response

    def _get_response_none_deprecation(self, get_response):
        if get_response is None:
            warnings.warn(
                'Passing None for the middleware get_response argument is '
                'deprecated.',
                RemovedInDjango40Warning, stacklevel=3,
            )

```
按照WSGI协议,调用中间件的时候会去调用middleware.__call__()方法,根据call方法，当request请求到来时，会先经过**process_request**方法,如果该middleware.process_request()返回非空,则直接调用**process_response**,此时不会在调用接下去的midlleware和WsgiApp.这里可以注意到__call__方法的参数并不是**envrion,start_response**,而是**get_response()**.这是DJANGO自己定义的**WSGIHandler**。

```python
# WSGIHandler的父类 BaseHandler
class BaseHandler:
    ...

    def load_middleware(self, is_async=False):
        """
        Populate middleware lists from settings.MIDDLEWARE.

        Must be called after the environment is fixed (see __call__ in subclasses).
        """
        self._view_middleware = []
        self._template_response_middleware = []
        self._exception_middleware = []

        get_response = self._get_response_async if is_async else self._get_response
        handler = convert_exception_to_response(get_response)
        handler_is_async = is_async
        for middleware_path in reversed(settings.MIDDLEWARE):
            middleware = import_string(middleware_path)
            # print(middleware)
            middleware_can_sync = getattr(middleware, 'sync_capable', True)
            middleware_can_async = getattr(middleware, 'async_capable', False)
            if not middleware_can_sync and not middleware_can_async:
                raise RuntimeError(
                    'Middleware %s must have at least one of '
                    'sync_capable/async_capable set to True.' % middleware_path
                )
            elif not handler_is_async and middleware_can_sync:
                middleware_is_async = False
            else:
                middleware_is_async = middleware_can_async
            try:
                # Adapt handler, if needed.
                adapted_handler = self.adapt_method_mode(
                    middleware_is_async, handler, handler_is_async,
                    debug=settings.DEBUG, name='middleware %s' % middleware_path,
                )
                mw_instance = middleware(adapted_handler) # 
                print(mw_instance)
            except MiddlewareNotUsed as exc:
                if settings.DEBUG:
                    if str(exc):
                        logger.debug('MiddlewareNotUsed(%r): %s', middleware_path, exc)
                    else:
                        logger.debug('MiddlewareNotUsed: %r', middleware_path)
                continue
            else:
                handler = adapted_handler # 下次循环,即下个中间件的的get_response即使就是上个中间件的实例.middleware(get_response)

            if mw_instance is None:
                raise ImproperlyConfigured(
                    'Middleware factory %s returned None.' % middleware_path
                )

            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(
                    0,
                    self.adapt_method_mode(is_async, mw_instance.process_view),
                )
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.append(
                    self.adapt_method_mode(is_async, mw_instance.process_template_response),
                )
            if hasattr(mw_instance, 'process_exception'):
                # The exception-handling stack is still always synchronous for
                # now, so adapt that way.
                self._exception_middleware.append(
                    self.adapt_method_mode(False, mw_instance.process_exception),
                )

            handler = convert_exception_to_response(mw_instance)
            handler_is_async = middleware_is_async

        # Adapt the top of the stack, if needed.
        handler = self.adapt_method_mode(is_async, handler, handler_is_async)
        # We only assign to this when initialization is complete as it is used
        # as a flag for initialization being complete.
        self._middleware_chain = handler
        print(">>> 加载中间件",self._middleware_chain)

    ...

    def get_response(self, request):
        """Return an HttpResponse object for the given HttpRequest."""
        # Setup default url resolver for this thread
        set_urlconf(settings.ROOT_URLCONF)
        response = self._middleware_chain(request)
        response._resource_closers.append(request.close)
        if response.status_code >= 400:
            log_response(
                '%s: %s', response.reason_phrase, request.path,
                response=response,
                request=request,
            )
        return response


## 对 middleware 实例进行封装
def convert_exception_to_response(get_response):
    """
    Wrap the given get_response callable in exception-to-response conversion.

    All exceptions will be converted. All known 4xx exceptions (Http404,
    PermissionDenied, MultiPartParserError, SuspiciousOperation) will be
    converted to the appropriate response, and all other exceptions will be
    converted to 500 responses.

    This decorator is automatically applied to all middleware to ensure that
    no middleware leaks an exception and that the next middleware in the stack
    can rely on getting a response instead of an exception.
    """
    if asyncio.iscoroutinefunction(get_response):
        @wraps(get_response)
        async def inner(request):
            try:
                response = await get_response(request)
            except Exception as exc:
                response = await sync_to_async(response_for_exception, thread_sensitive=False)(request, exc)
            return response
        return inner
    else:
        @wraps(get_response)
        def inner(request):
            try:
                response = get_response(request) # get_response相当于load_middlerware中的mw_instance
            except Exception as exc:
                response = response_for_exception(request, exc)
            return response
        return inner

```


django在启动监听服务的时候会调用**load_middleware**对middleware进行实例化，在整个生命周期只会实例化一次.查看load_middleware中的for-loop(对middleware_list倒序遍历).这里简单实现了一个中间件的递归,假设我们有以下中间件列表:[middleware1,middleware2,middleware3],则循环开始前,**get_response**参数为**self._get_response()**,则实例化**middleware3**是可简化为**middleware3(self._get_response)**,然后赋值给handler,进入第二次循环.实例化**middleware1**时相当于**middleware2(middleware3(self._get_response))**,然后再赋值给handler.接着是第三个**middleware2**,最后的**handler**相当于**middleware1(middleware2(middleware3(self._get_response)))**

所以,当request到来时,先是通过了middleware调用链**response = self._middleware_chain(request)**,既可以当成为**response = middleware1(middleware2(middleware3(self._get_response))).__call__(request)**

我们再通过MiddleWareMixin中的_call__方法
```python

    def __call__(self, request):
        # Exit out to async mode, if needed
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        response = response or self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response
```
可以得出以下几点结论:
* 当中间件列表中,只要有*process_request*返回非None值,则直接结束该request,不会再往下递归调用,而是直接返回,并从该中间件开始调用*process_response*处理返回的结果.

* 要想把中间件的*process_request*传递给下个中间件处理,可以把处理结果放在*request对象中*

* 中间件调用完成后,最终调用**WSGIHandler()._get_response()**