## AsyncModelForm

the `AsyncModelForm` is a subclass of django's [ModelForm](https://docs.djangoproject.com/en/5.1/topics/forms/modelforms/#django.forms.ModelForm)
but `asave()` has been added to support async saving.

if `asave()` is used with `commit=False`, a `asave_m2m()` will be available to use.

*Example myapp/models.py*:
```python
from django.db import models
from django.urls import reverse


class Author(models.Model):
    name = models.CharField(max_length=200)

    def get_absolute_url(self):
        return reverse("author-detail", kwargs={"pk": self.pk})
```

*Example myapp/forms.py*:
```python
from django_async_extensions.forms import AsyncModelForm
from myapp.models import Author


class AuthorForm(AsyncModelForm):
    model = Author
    fields = ("name",)
```

#### Construction

normally you instantiate a field like this:
`form = AuthorForm(data)`
and that works fine

but sometimes you pass in an instance to the form (e.g: you are building an update view)
```pycon
>>> author = Author.objects.get(pk=1)
>>> form = AuthorForm(instance=author)
```

in this case, you will probably face an error saying you can't do synchronous operations in an async environment
for situations like this, we provide an alternative contractor called `from_async()`

```pycon
author = await Author.objects.aget(pk=1)
form = await AuthorForm.from_async(instance=author)
```

note that `from_async()` is an async method that should be `await`ed

#### validation
if a validator requires database access (e.g: unique validator) you will face a problem in async views
to solve that, we provide a few methods

* ais_valid
```python
if await form.ais_valid():
    # handle data
```
an awaitable version of django's [Form.is_valid](https://docs.djangoproject.com/en/5.1/ref/forms/api/#django.forms.Form.is_valid)

* aerrors (property)
```pycon
>>> errors = await form.aerrors
```
an awaitable version of django's [Form.errors](https://docs.djangoproject.com/en/5.1/ref/forms/api/#django.forms.Form.errors)

* afull_clean
```python
await form.afull_clean()
```
an awaitable version of django's `Form.full_clean`, you typically don't call this manually.



#### Manual form rendering
django's templating system is fully sync, so you can't call async methods and functions in the templates
you can call sync methods and render the page using `asgiref.sync.sync_to_async`, or you can gather the data in your view and pass them in as context.

a few methods have been provided so forms can be rendered manually:

1. arender: an `await`able version of django's [Form.render](https://docs.djangoproject.com/en/5.1/ref/forms/api/#render)
2. aas_div: an `await`able version of django's [Form.as_div](https://docs.djangoproject.com/en/5.1/ref/forms/api/#as-div)
3. aas_p: an `await`able version of django's [Form.as_p](https://docs.djangoproject.com/en/5.1/ref/forms/api/#django.forms.Form.as_p)
4. aas_ul: an `await`able version of django's [Form.as_ul](https://docs.djangoproject.com/en/5.1/ref/forms/api/#as-ul)
5. aas_table: an `await`able version of django's [Form.as_table](https://docs.djangoproject.com/en/5.1/ref/forms/api/#as-table)


note that the sync versions are still available.

___
**WARNING!**

forms are not fully async capable, this class has been added to make saving a bit easier, 
but still some form futures are not supported, if you encounter any problems, use `asgiref.sync.sync_to_async` on it
---
