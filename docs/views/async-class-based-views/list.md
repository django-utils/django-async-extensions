## AsyncListView

`AsyncListView` generic view

```python
from django_async_extensions.aviews.generic import AsyncListView

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

1. [django.views.generic.list.MultipleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-multiple-object/#django.views.generic.list.MultipleObjectTemplateResponseMixin)
2. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
3. [django_async_extensions.aviews.generic.list.AsyncBaseListView](list.md#asyncbaselistview)
4. [django_async_extensions.aviews.generic.list.AsyncMultipleObjectMixin](list.md#asyncmultipleobjectmixin)
5. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
6. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
7. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


## Base classes
some of the base classes for `ListView` have been re-written as async:

### AsyncMultipleObjectMixin
like [MultipleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-multiple-object/#django.views.generic.list.MultipleObjectMixin) but `get_queryset()`, `paginate_queryset()` and `get_context_data()` methods are async.

### AsyncBaseListView
like [BaseListView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.list.BaseListView) but `get()` method is async.
