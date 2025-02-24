from itertools import chain

from asgiref.sync import sync_to_async

from django.forms.models import ModelForm

from django_async_extensions.aforms.utils import AsyncRenderableFormMixin


class AsyncModelForm(AsyncRenderableFormMixin, ModelForm):
    @classmethod
    async def from_async(cls, *args, **kwargs):
        return await sync_to_async(cls)(*args, **kwargs)

    @property
    async def aerrors(self):
        if self._errors is None:
            await self.afull_clean()
        return self._errors

    async def ais_valid(self):
        return self.is_bound and not await self.aerrors

    async def afull_clean(self):
        return await sync_to_async(self.full_clean)()

    async def _asave_m2m(self):
        """
        Save the many-to-many fields and generic relations for this form.
        """
        cleaned_data = self.cleaned_data
        exclude = self._meta.exclude
        fields = self._meta.fields
        opts = self.instance._meta
        # Note that for historical reasons we want to include also
        # private_fields here. (GenericRelation was previously a fake
        # m2m field).
        for f in chain(opts.many_to_many, opts.private_fields):
            if not hasattr(f, "save_form_data"):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                # TODO: when an async version of save_form_data is available,
                #  replace this to await that instead.
                await sync_to_async(f.save_form_data)(
                    self.instance, cleaned_data[f.name]
                )

    async def asave(self, commit=True):
        """
        Save this form's self.instance object if commit=True. Otherwise, add
        a save_m2m() method to the form which can be called after the instance
        is saved manually at a later time. Return the model instance.
        """
        await sync_to_async(self.full_clean)()
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate."
                % (
                    self.instance._meta.object_name,
                    "created" if self.instance._state.adding else "changed",
                )
            )
        if commit:
            # If committing, save the instance and the m2m data immediately.
            await self.instance.asave()
            await self._asave_m2m()
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.asave_m2m = self._asave_m2m
        return self.instance

    asave.alters_data = True
