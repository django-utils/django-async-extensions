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
4. the inheritance tree is different so the ancestors behaviour also applies here.

*Ancestors (MRO)*:

1. [django.views.generic.detail.SingleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#singleobjecttemplateresponsemixin)
2. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
3. [django_async_extensions.aviews.generic.detail.AsyncBaseDetailView](detail.md#asyncbasedetailview)
4. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](detail.md#asyncsingleobjectmixin)
5. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
6. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
7. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


## Base classes
some of the base classes for `DetailView` have been re-written as async:

#### AsyncSingleObjectMixin

like [SingleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#django.views.generic.detail.SingleObjectMixin)
with these differences:

* inherits from [AsyncContextMixin](base.md#asynccontextmixin)
* `get_object()` method is async.
* `get_queryset()` method is async.
* `get_context_data()` method is async.

#### AsyncBaseDetailView

like [BaseDetailView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.detail.BaseDetailView) but `get()` is async.
