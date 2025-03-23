## AsyncMiddlewareMixin

a base class to create async only middlewares.

it is very similar to django's [MiddlewareMixin](https://docs.djangoproject.com/en/5.1/topics/http/middleware/#upgrading-pre-django-1-10-style-middleware)
with the following specification:

`__call__` method is async, so you need to `await` the middleware instance.
```pycon
>>> middleware = AsyncMiddlewareMixin(get_response)
>>> await middleware()
```
where `get_response` is an async function, sync functions are not supported and will raise an error.

----------------------------

other methods are as follows:

* `process_request` and `process_response` are `await`ed inside the middleware and have to be async

* `process_view` and `process_template_response` can be either sync or async, but **async is preferred**, if it's sync django will wrap it as async which might have slight performance reduction.

* `process_exception` can be either sync or async, but **sync is preferred**, if async is used django wraps the method to be called synchronously.
