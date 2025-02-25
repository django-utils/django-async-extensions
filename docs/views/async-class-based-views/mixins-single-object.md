## AsyncSingleObjectMixin

like [SingleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#django.views.generic.detail.SingleObjectMixin)
with these differences:

* inherits from [AsyncContextMixin](mixins-simple.md#asynccontextmixin)
* `get_object()` method is async.
* `get_queryset()` method is async.
* `get_context_data()` method is async.

## AsyncSingleObjectTemplateResponseMixin

like django's [SingleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#singleobjecttemplateresponsemixin)
but inherits from [AsyncTemplateResponseMixin](mixins-simple.md#asynctemplateresponsemixin)
