## AsyncListView

`AsyncListView` generic view

```python
from django_async_extensions.views.generic import AsyncListView

class MyListView(AsyncListView):
    model = MyModel
```

`AsyncListView` works similarly to django's [ListView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#listview) but with a few differences:

1. `get_queryset()` method is async.
2. `paginate_queryset()` method is async.
3. `get_context_data()` method is async.
4. `get()` method is async.
5. [AsyncPaginator](../../core/async-paginator.md) is used for pagination instead of django's regular [Paginator](https://docs.djangoproject.com/en/5.1/ref/paginator/#django.core.paginator.Paginator).
6. the inheritance tree is different so the ancestors behaviour also applies here.

*Ancestors (MRO)*:

1. [django-async-extensions.views.generic.list.AsyncMultipleObjectTemplateResponseMixin](mixins-multiple-object.md#asyncmultipleobjecttemplateresponsemixin)
2. [django-async-extensions.views.generic.base.AsyncTemplateResponseMixin](mixins-simple.md#asynctemplateresponsemixin)
3. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
4. [django_async_extensions.views.generic.list.AsyncBaseListView](list.md#asyncbaselistview)
5. [django_async_extensions.views.generic.list.AsyncMultipleObjectMixin](mixins-multiple-object.md#asyncmultipleobjectmixin)
6. [django_async_extensions.views.generic.base.AsyncContextMixin](mixins-simple.md#asynccontextmixin)
7. [django_async_extensions.views.generic.base.AsyncView](base.md#asyncview)
8. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


## Base classes
some of the base classes for `ListView` have been re-written as async:

### AsyncBaseListView
like [BaseListView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.list.BaseListView) but `get()` method is async.
