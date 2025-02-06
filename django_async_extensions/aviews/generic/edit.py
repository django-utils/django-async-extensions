from django.core.exceptions import ImproperlyConfigured
from django.forms import models as model_forms
from django.http import HttpResponseRedirect
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import FormMixin

from django_async_extensions.aviews.generic.base import AsyncView
from django_async_extensions.aviews.generic.detail import (
    AsyncSingleObjectMixin,
)


class AsyncFormMixin(FormMixin):
    async def get_form_class(self):
        """Return the form class to use."""
        # this is async so subclasses can be of the same nature
        return self.form_class

    async def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = await self.get_form_class()
        return form_class(**self.get_form_kwargs())

    async def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url())

    async def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(await self.get_context_data(form=form))

    async def get_context_data(self, **kwargs):
        """Insert the form into the context dict."""
        if "form" not in kwargs:
            kwargs["form"] = await self.get_form()
        return ContextMixin().get_context_data(**kwargs)


class AsyncModelFormMixin(AsyncFormMixin, AsyncSingleObjectMixin):
    """Provide a way to show and handle a ModelForm in a request."""

    fields = None

    async def get_form_class(self):
        """Return the form class to use in this view."""
        if self.fields is not None and self.form_class:
            raise ImproperlyConfigured(
                "Specifying both 'fields' and 'form_class' is not permitted."
            )
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif getattr(self, "object", None) is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                queryset = await self.get_queryset()
                model = queryset.model

            if self.fields is None:
                raise ImproperlyConfigured(
                    "Using ModelFormMixin (base class of %s) without "
                    "the 'fields' attribute is prohibited." % self.__class__.__name__
                )

            return model_forms.modelform_factory(model, fields=self.fields)

    async def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = await form.asave()
        return super().form_valid(form)


class AsyncProcessFormView(AsyncView):
    """Render a form on GET and processes it on POST."""

    async def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        return self.render_to_response(await self.get_context_data())

    async def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = await self.get_form()
        if form.is_valid():
            return await self.form_valid(form)
        else:
            return await self.form_invalid(form)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    async def put(self, *args, **kwargs):
        return await self.post(*args, **kwargs)


class AsyncBaseFormView(AsyncFormMixin, AsyncProcessFormView):
    """A base view for displaying a form."""


class AsyncFormView(TemplateResponseMixin, AsyncBaseFormView):
    """A view for displaying a form and rendering a template response."""
