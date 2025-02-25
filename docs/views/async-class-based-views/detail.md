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

1. [django-async-extensions.aviews.generic.detail.AsyncSingleObjectTemplateResponseMixin](mixins-single-object.md#asyncsingleobjecttemplateresponsemixin)
2. [django-async-extensions.aviews.generic.base.AsyncTemplateResponseMixin](mixins-simple.md#asynctemplateresponsemixin)
3. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
4. [django_async_extensions.aviews.generic.detail.AsyncBaseDetailView](detail.md#asyncbasedetailview)
5. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](mixins-single-object.md#asyncsingleobjectmixin)
6. [django_async_extensions.aviews.generic.base.AsyncContextMixin](mixins-simple.md#asynccontextmixin)
7. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
8. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


## Base classes
some of the base classes for `DetailView` have been re-written as async:

#### AsyncBaseDetailView

like [BaseDetailView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-display/#django.views.generic.detail.BaseDetailView) but `get()` is async and the ancestors are different.

*Ancestors (MRO)*:

1. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](mixins-single-object.md#asyncsingleobjectmixin)
2. [django_async_extensions.aviews.generic.base.AsyncContextMixin](mixins-simple.md#asynccontextmixin)
3. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
4. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)
