## AsyncDetailView

`AsyncDetailView` generic view is provided

```python
from django_async_extensions.aviews.generic import AsyncDetailView

class MyDetailView(AsyncDetailView):
    model = MyModel
```

`AsyncDetailView` is similar to django's [DetailView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#detailview) but with a few differences:

1. `get_object()` method is async.
2. `get_queryset()` method is async.
3. `get()` method is async.
4. `AsyncDetailView` inherits from [AsyncView](async-class-based-views.md#asyncview) so anything mentioned there also applies here.


## Base classes
some of the base classes for `DetailView` have been re-written as async:

#### AsyncSingleObjectMixin

like [SingleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#django.views.generic.detail.SingleObjectMixin) but `get_object()` and `get_queryset()` are async.

#### AsyncBaseDetailView

like [BaseDetailView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.detail.BaseDetailView) but `get()` is async.
