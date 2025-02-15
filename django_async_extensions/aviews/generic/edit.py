from django.core.exceptions import ImproperlyConfigured
from django.forms import models as model_forms
from django.http import HttpResponseRedirect
from django.views.generic.base import TemplateResponseMixin

from django_async_extensions.aviews.generic.base import AsyncView, AsyncContextMixin
from django_async_extensions.aviews.generic.detail import (
    AsyncSingleObjectMixin,
)


class AsyncFormMixin(AsyncContextMixin):
    """Provide a way to show and handle a form in a request."""

    initial = {}
    form_class = None
    success_url = None
    prefix = None

    def get_initial(self):
        """Return the initial data to use for forms on this view."""
        return self.initial.copy()

    def get_prefix(self):
        """Return the prefix to use for forms."""
        return self.prefix

    async def get_form_class(self):
        """Return the form class to use."""
        # this is async so subclasses can be of the same nature
        return self.form_class

    async def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = await self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)  # success_url may be lazy

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
        return await super().get_context_data(**kwargs)


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

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs

    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        if self.success_url:
            url = self.success_url.format(**self.object.__dict__)
        else:
            try:
                url = self.object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the Model."
                )
        return url

    async def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = await form.asave()
        return await super().form_valid(form)


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
