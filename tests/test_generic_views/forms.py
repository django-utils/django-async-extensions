from asgiref.sync import sync_to_async
from django import forms

from .models import Author, Artist


class ArtistModelForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = "__all__"  # noqa: DJ007

    async def asave(self, commit=True):
        # temp, until async model form is added
        return await sync_to_async(self.save)(commit=commit)


class AuthorModelForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = "__all__"  # noqa: DJ007

    async def asave(self, commit=True):
        # temp, until async model form is added
        return await sync_to_async(self.save)(commit=commit)


class AuthorForm(forms.ModelForm):
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        model = Author
        fields = ["name", "slug"]

    async def asave(self, commit=True):
        # temp, until async model form is added
        return await sync_to_async(self.save)(commit=commit)


class ContactForm(forms.Form):
    name = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)


class ConfirmDeleteForm(forms.Form):
    confirm = forms.BooleanField()

    def clean(self):
        cleaned_data = super().clean()
        if "confirm" not in cleaned_data:
            raise forms.ValidationError("You must confirm the delete.")
