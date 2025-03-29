from functools import wraps

from asgiref.sync import async_to_sync, iscoroutinefunction, sync_to_async


def decorator_from_middleware_with_args(middleware_class, async_only=True):
    """
    Like decorator_from_middleware, but return a function
    that accepts the arguments to be passed to the middleware_class.
    Use like::

         cache_page = decorator_from_middleware_with_args(CacheMiddleware)
         # ...

         @cache_page(3600)
         def my_view(request):
             # ...
    """
    return make_middleware_decorator(middleware_class, async_only=async_only)


def decorator_from_middleware(middleware_class, async_only=True):
    """
    Given a middleware class (not an instance), return a view decorator. This
    lets you use middleware functionality on a per-view basis. The middleware
    is created with no params passed.
    """
    return make_middleware_decorator(middleware_class, async_only=async_only)()


def make_middleware_decorator(middleware_class, async_only=True):
    def _make_decorator(*m_args, **m_kwargs):
        def _decorator(view_func):
            _view_func = view_func
            if all(
                [
                    not iscoroutinefunction(view_func),
                    not iscoroutinefunction(getattr(view_func, "__call__", None)),
                    async_only,
                ]
            ):
                _view_func = sync_to_async(view_func)
            middleware = middleware_class(_view_func, *m_args, **m_kwargs)

            async def _pre_process_request(request, *args, **kwargs):
                if hasattr(middleware, "process_request"):
                    result = await middleware.process_request(request)
                    if result is not None:
                        return result
                if hasattr(middleware, "process_view"):
                    if iscoroutinefunction(middleware.process_view):
                        result = await middleware.process_view(
                            request, view_func, args, kwargs
                        )
                    else:
                        result = await sync_to_async(middleware.process_view)(
                            request, view_func, args, kwargs
                        )
                    if result is not None:
                        return result
                return None

            async def _process_exception(request, exception):
                if hasattr(middleware, "process_exception"):
                    if iscoroutinefunction(middleware.process_exception):
                        result = await middleware.process_exception(request, exception)
                    else:
                        result = await sync_to_async(middleware.process_exception)(
                            request, exception
                        )
                    if result is not None:
                        return result
                raise

            async def _post_process_request(request, response):
                if hasattr(response, "render") and callable(response.render):
                    if hasattr(middleware, "process_template_response"):
                        if iscoroutinefunction(middleware.process_template_response):
                            response = await middleware.process_template_response(
                                request, response
                            )
                        else:
                            response = await sync_to_async(
                                middleware.process_template_response
                            )(request, response)
                    # Defer running of process_response until after the template
                    # has been rendered:
                    if hasattr(middleware, "process_response"):

                        async def callback(response):
                            return await middleware.process_response(request, response)

                        response.add_post_render_callback(async_to_sync(callback))
                else:
                    if hasattr(middleware, "process_response"):
                        return await middleware.process_response(request, response)
                return response

            if iscoroutinefunction(view_func) or iscoroutinefunction(
                getattr(view_func, "__call__", view_func)
            ):

                async def _view_wrapper(request, *args, **kwargs):
                    result = await _pre_process_request(request, *args, **kwargs)
                    if result is not None:
                        return result

                    try:
                        response = await view_func(request, *args, **kwargs)
                    except Exception as e:
                        result = await _process_exception(request, e)
                        if result is not None:
                            return result

                    return await _post_process_request(request, response)

            else:

                def _view_wrapper(request, *args, **kwargs):
                    result = async_to_sync(_pre_process_request)(
                        request, *args, **kwargs
                    )
                    if result is not None:
                        return result

                    try:
                        response = view_func(request, *args, **kwargs)
                    except Exception as e:
                        result = async_to_sync(_process_exception)(request, e)
                        if result is not None:
                            return result

                    return async_to_sync(_post_process_request)(request, response)

            return wraps(view_func)(_view_wrapper)

        return _decorator

    return _make_decorator
