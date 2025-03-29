`django_async_extensions.utils.decorators.decorator_from_middleware` and 
`django_async_extensions.utils.decorators.decorator_from_middleware_with_args`
are provided to decorate a view with an async middleware directly.

they work almost exactly like django's [decorator_from_middleware](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.decorators.decorator_from_middleware)
and [decorator_from_middleware_with_args](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.decorators.decorator_from_middleware_with_args) 
but it expects an async middleware as described in [AsyncMiddlewareMixin](base.md)

with an async view
```python
from django.http.response import HttpResponse

from django_async_extensions.middleware.base import AsyncMiddlewareMixin
from django_async_extensions.utils.decorators import decorator_from_middleware

class MyAsyncMiddleware(AsyncMiddlewareMixin):
    async def process_request(self, request):
        return HttpResponse()


deco = decorator_from_middleware(MyAsyncMiddleware)


@deco
async def my_view(request):
    return HttpResponse()
```


if your view is sync, it'll be wrapped in `sync_to_async` before getting passed down to middleware.

if you need, you can disable this by passing `async_only=False`.
note that the middlewares presented in this package will error if you do that, so you have to override the `__init__()` and `__call__()` methods to handle that.

```python
from django.http.response import HttpResponse

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from django_async_extensions.middleware.base import AsyncMiddlewareMixin
from django_async_extensions.utils.decorators import decorator_from_middleware

class MyMiddleware(AsyncMiddlewareMixin):
    sync_capable = True
    
    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        
        self.async_mode = iscoroutinefunction(self.get_response) or iscoroutinefunction(
            getattr(self.get_response, "__call__", None)
        )
        if self.async_mode:
            # Mark the class as async-capable.
            markcoroutinefunction(self)
            
    async def __call__(self, request):
        response = None
        if hasattr(self, "process_request"):
            response = await self.process_request(request)
        response = response or self.get_response(request) # here call the method in a sync manner, or handle it in another way
        if hasattr(self, "process_response"):
            response = await self.process_response(request, response)
        return response

    async def process_request(self, request):
        return HttpResponse()


deco = decorator_from_middleware(MyMiddleware, async_only=False)


@deco
def my_view(request):
    return HttpResponse()
```
