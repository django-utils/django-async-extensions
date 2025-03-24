`django_async_extensions.utils.decorators.decorator_from_middleware` and 
`django_async_extensions.utils.decorators.decorator_from_middleware_with_args`
are provided to decorate a view with an async middleware directly.

they work almost exactly like django's [decorator_from_middleware](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.decorators.decorator_from_middleware)
and [decorator_from_middleware_with_args](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.decorators.decorator_from_middleware_with_args) 
but it expects an async middleware as described in [AsyncMiddlewareMixin](base.md)

**Important:** if you are using a middleware that inherits from [AsyncMiddlewareMixin](base.md) you can only decorate async views
if you need to decorate a sync view change middleware's `__init__()` method to accept async `get_response` argument.

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


if you need to use a sync view design your middleware like this
```python
from django_async_extensions.middleware.base import AsyncMiddlewareMixin

from asgiref.sync import iscoroutinefunction, markcoroutinefunction


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

        super().__init__()
```
