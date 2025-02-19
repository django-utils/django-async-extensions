## Generic editing views

### AsyncFormView

`AsyncFormView` works like django's [FormView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#formview)
but the inheritance tree has changed to work asynchronously.

*Ancestors (MRO)*:

1. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
2. [django_async_extensions.aviews.generic.edit.AsyncBaseFormView](edit.md#asyncbaseformview)
3. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
4. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
5. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
6. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
7. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


*Example myapp/forms.py*
```python
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)

    def send_email(self):
        # send some email
        pass
```

*Example myapp/views.py*
```python
from myapp.forms import ContactForm
from django_async_extensions.aviews.generic.edit import AsyncFormView


class ContactFormView(AsyncFormView):
    template_name = "contact.html"
    form_class = ContactForm
    success_url = "/thanks/"

    async def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        form.send_email()
        return await super().form_valid(form)
```

*Example myapp/contact.html*
```html
<form method="post">{% csrf_token %}
    {{ form.as_p }}
    <input type="submit" value="Send message">
</form>
```

## Base Class

### AsyncBaseFormView
A base view for displaying a form. It is not intended to be used directly,
but rather as a parent class of the django_async_extensions.aviews.generic.edit.AsyncFormView or other views displaying a form.

similar to django's [BaseFormView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#django.views.generic.edit.BaseFormView)
but the ancestors are different:

* [AsyncFormMixin](mixins-editing.md#asyncformmixin)
* [AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
