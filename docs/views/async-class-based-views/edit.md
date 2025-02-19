## Generic editing views

---
**NOTE**

some of the examples in this page assumes an `Author` model has been defined as follows in `myapp/models.py`

```python
from django.db import models
from django.urls import reverse


class Author(models.Model):
    name = models.CharField(max_length=200)

    def get_absolute_url(self):
        return reverse("author-detail", kwargs={"pk": self.pk})
```


---
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

### AsyncCreateView

`AsyncCreateView` works similar to django's [CreateView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#createview)
if no form is specified for this to view, [AsyncModelForm](../../forms/model_form.md#asyncmodelform) is used by default, you can change this behaviour by specifying `base_form_class`in the view.
any form you use with this view needs to define a `asave()` method.
note that `form_class` and `base_form_class` are different:
`form_class` is the form you design to work with your data,
`base_form_class` is used to make a default form when no `form_class` is specified.
also the inheritance tree is different to support async operation.

*Ancestors (MRO)*:

1. [django.views.generic.detail.SingleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#singleobjecttemplateresponsemixin)
2. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
3. [django_async_extensions.aviews.generic.edit.AsyncBaseCreateView](edit.md#asyncbasecreateview)
4. [django_async_extensions.aviews.generic.edit.AsyncModelFormMixin](mixins-editing.md#asyncmodelformmixin)
5. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
6. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](detail.md#asyncsingleobjectmixin)
7. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
8. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
9. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
10. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


*Example myapp/views.py*
```python
from django_async_extensions.aviews.generic.edit import AsyncCreateView
from myapp.models import Author


class AuthorCreateView(AsyncCreateView):
    model = Author
    fields = ["name"]
```

*Example myapp/author_form.html*
```html
<form method="post">{% csrf_token %}
    {{ form.as_p }}
    <input type="submit" value="Save">
</form>
```

*Example using a different model form as a factory*:
```python
from django_async_extensions.aviews.generic.edit import AsyncCreateView
from myapp.models import Author
from myapp.forms import ModelForm

class AuthorCreateView(AsyncCreateView):
    model = Author
    fields = ["name"]
    base_form_class = ModelForm
```


### AsyncUpdateView

`AsyncUpdateView` works similar to django's [UpdateView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#updateview)
if no form is specified for this to view, [AsyncModelForm](../../forms/model_form.md#asyncmodelform) is used by default, you can change this behaviour by specifying `base_form_class`in the view.
any form you use with this view needs to define a `asave()` method.
note that `form_class` and `base_form_class` are different:
`form_class` is the form you design to work with your data,
`base_form_class` is used to make a default form when no `form_class` is specified.
also the inheritance tree is different to support async operation.

*Ancestors (MRO)*:

1. [django.views.generic.detail.SingleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#singleobjecttemplateresponsemixin)
2. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
3. [django_async_extensions.aviews.generic.edit.AsyncBaseUpdateView](edit.md#asyncbasecreateview)
4. [django_async_extensions.aviews.generic.edit.AsyncModelFormMixin](mixins-editing.md#asyncmodelformmixin)
5. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
6. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](detail.md#asyncsingleobjectmixin)
7. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
8. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
9. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
10. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


*Example myapp/views.py*
```python
from django_async_extensions.aviews.generic.edit import AsyncUpdateView
from myapp.models import Author


class AuthorCreateView(AsyncUpdateView):
    model = Author
    fields = ["name"]
```

*Example myapp/author_form.html*
```html
<form method="post">{% csrf_token %}
    {{ form.as_p }}
    <input type="submit" value="Save">
</form>
```

*Example using a different model form as a factory*:
```python
from django_async_extensions.aviews.generic.edit import AsyncUpdateView
from myapp.models import Author
from myapp.forms import ModelForm

class AuthorCreateView(AsyncUpdateView):
    model = Author
    fields = ["name"]
    base_form_class = ModelForm
```

### AsyncDeleteView
`AsyncDeleteView` works similar to django's [DeleteView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#deleteview)
but it's been modified to work as an async view.

*Ancestors (MRO)*:

1. [django.views.generic.detail.SingleObjectTemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-single-object/#singleobjecttemplateresponsemixin)
2. [django_async_extensions.aviews.generic.edit.AsyncBaseDeleteView]()
3. [django_async_extensions.aviews.generic.edit.AsyncDeletionMixin](mixins-editing.md#asyncdeletionmixin)
4. [django_async_extensions.aviews.generic.edit.AsyncFormView](mixins-editing.md#asyncdeletionmixin)
5. [django.views.generic.base.TemplateResponseMixin](https://docs.djangoproject.com/en/5.1/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin)
6. [django_async_extensions.aviews.generic.edit.AsyncBaseFormView](edit.md#asyncbaseformview)
7. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
8. [django_async_extensions.aviews.generic.detail.AsyncBaseDetailView](detail.md#asyncbasedetailview)
9. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](detail.md#asyncsingleobjectmixin)
10. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
11. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
12. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
13. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View) 


## Base Class

### AsyncBaseFormView
A base view for displaying a form. It is not intended to be used directly,
but rather as a parent class of the django_async_extensions.aviews.generic.edit.AsyncFormView or other views displaying a form.

similar to django's [BaseFormView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#django.views.generic.edit.BaseFormView)
but the ancestors are different.

*Ancestors (MRO)*:

1. [django_async_extensions.aviews.generic.edit.AsyncBaseFormView](edit.md#asyncbaseformview)
2. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
3. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
4. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
5. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
6. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)


### AsyncBaseCreateView
A base view for creating a new object instance. It is not intended to be used directly, but rather as a parent class of the [django_async_extensions.aviews.generic.edit.AsyncCreateView](edit.md#asynccreateview).

similar to django's [BaseCreateView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/generic-editing/#django.views.generic.edit.BaseCreateView) but asyncified.

*Ancestors (MRO)*:

1. [django_async_extensions.aviews.generic.edit.AsyncModelFormMixin](mixins-editing.md#asyncmodelformmixin)
2. [django_async_extensions.aviews.generic.edit.AsyncFormMixin](mixins-editing.md#asyncformmixin)
3. [django_async_extensions.aviews.generic.base.AsyncContextMixin](base.md#asynccontextmixin)
4. [django_async_extensions.aviews.generic.detail.AsyncSingleObjectMixin](detail.md#asyncsingleobjectmixin)
5. [django_async_extensions.aviews.generic.edit.AsyncProcessFormMixin](mixins-editing.md#asyncprocessformview)
6. [django_async_extensions.aviews.generic.base.AsyncView](base.md#asyncview)
7. [django.views.generic.base.View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View)
