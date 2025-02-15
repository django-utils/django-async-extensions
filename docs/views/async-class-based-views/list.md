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
6. `AsyncListView` inherits from [AsyncView](base.md#asyncview) so anything mentioned there also applies here.

## Base classes
some of the base classes for `ListView` have been re-written as async:

### AsyncMultipleObjectMixin
like [MultipleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-multiple-object/#django.views.generic.list.MultipleObjectMixin) but `get_queryset()`, `paginate_queryset()` and `get_context_data()` methods are async.

### AsyncBaseListView
like [BaseListView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.list.BaseListView) but `get()` method is async.
