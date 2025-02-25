## AsyncMultipleObjectMixin
like [MultipleObjectMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-multiple-object/#django.views.generic.list.MultipleObjectMixin) but `get_queryset()`, `paginate_queryset()` and `get_context_data()` methods are async.

## AsyncMultipleObjectTemplateResponseMixin
like django's [AsyncMultipleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-multiple-object/#multipleobjecttemplateresponsemixin)
but inherits from [AsyncTemplateResponseMixin](mixins-simple.md#asynctemplateresponsemixin)
