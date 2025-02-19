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
from django_async_extensions.aforms import AsyncModelForm
from myapp.models import Author


class AuthorForm(AsyncModelForm):
    model = Author
    fields = ("name",)
```


___
**WARNING!**

forms are not fully async capable, this class has been added to make saving a bit easier, 
but still some form futures are not supported, if you encounter any problems, use `asgiref.sync.sync_to_async` on it
---
