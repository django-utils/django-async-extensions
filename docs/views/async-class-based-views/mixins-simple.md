## AsyncContextMixin
an async version of django's [ContextMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.ContextMixin)
the only difference is that the `get_context_data()` method is async.


## AsyncTemplateResponseMixin
an async version of django's [TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#templateresponsemixin)
the `render_to_response` method has been turned async to make database connections possible.
