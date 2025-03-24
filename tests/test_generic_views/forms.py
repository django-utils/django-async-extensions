from django import forms

from django_async_extensions.forms.models import AsyncModelForm

from .models import Author, Artist


class ArtistModelForm(AsyncModelForm):
    class Meta:
        model = Artist
        fields = "__all__"  # noqa: DJ007


class AuthorModelForm(AsyncModelForm):
    class Meta:
        model = Author
        fields = "__all__"  # noqa: DJ007


class AuthorForm(AsyncModelForm):
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        model = Author
        fields = ["name", "slug"]


class ContactForm(forms.Form):
    name = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)


class ConfirmDeleteForm(forms.Form):
    confirm = forms.BooleanField()

    def clean(self):
        cleaned_data = super().clean()
        if "confirm" not in cleaned_data:
            raise forms.ValidationError("You must confirm the delete.")
