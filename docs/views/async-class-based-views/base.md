## AsyncView

async CBVs are supported via the `AsyncView` class.

```python
from django_async_extensions.aviews.generic import AsyncView


class MyView(AsyncView):
    pass
```

the `AsyncView` works similar to django's [View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#view) class, with a few differences:

1. `AsyncView.as_view()` returns a coroutine.
2. `AsyncView.dispatch()` is an async function.
3. http handlers (`def get()`, `def post()`) are expected to be async.


## AsyncTemplateView

for easy use an async version of `TemplateView` is available

```python
from django_async_extensions.aviews.generic import AsyncTemplateView

class MyTemplateView(AsyncTemplateView):
    template_name = "template.html"
```

`AsyncTemplateView` works like django's [TemplateView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#templateview) except the inheritance tree is different, also the `get()` method is async.

*Ancestors (MRO)*:

1. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
2. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
3. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
4. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


## AsyncRedirectView

an async version of `RedirectView` is also available

```python
from django_async_extensions.aviews.generic import AsyncRedirectView

class ThisRedirectView(AsyncRedirectView):
    pattern_name = "that-view"
```

`AsyncRedirectView` works like django's [RedirectView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#redirectview) except that all http methods are async, and it inherits from [AsyncView](base.md#asyncview).

*Ancestors (MRO)*:

1. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
2. [django.views.generic.base.RedirectView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#redirectview)
3. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)

