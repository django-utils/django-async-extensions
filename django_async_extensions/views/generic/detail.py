from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.http import Http404
from django.utils.translation import gettext as _

from django_async_extensions.views.generic.base import (
    AsyncView,
    AsyncContextMixin,
    AsyncTemplateResponseMixin,
)


class AsyncSingleObjectMixin(AsyncContextMixin):
    """
    Provide the ability to retrieve a single object for further manipulation.
    """

    model = None
    queryset = None
    slug_field = "slug"
    context_object_name = None
    slug_url_kwarg = "slug"
    pk_url_kwarg = "pk"
    query_pk_and_slug = False

    async def get_object(self, queryset=None):
        """
        Return the object the view is displaying.

        Require `self.queryset` and a `pk` or `slug` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = await self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError(
                "Generic detail view %s must be called with either an object "
                "pk or a slug in the URLconf." % self.__class__.__name__
            )

        try:
            # Get the single item from the filtered queryset
            obj = await queryset.aget()
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    async def get_queryset(self):
        """
        Return the `QuerySet` that will be used to look up the object.

        This method is called by the default implementation of get_object() and
        may not be called if get_object() is overridden.
        """
        # this is implemented as an async function so user can overwrite it
        # and `await` on an ORM call without needing to rewrite `get_object`
        if self.queryset is None:
            if self.model:
                return self.model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a QuerySet. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
                )
        return self.queryset.all()

    def get_slug_field(self):
        """Get the name of a slug field to be used to look up by slug."""
        return self.slug_field

    def get_context_object_name(self, obj):
        """Get the name to use for the object."""
        if self.context_object_name:
            return self.context_object_name
        elif isinstance(obj, models.Model):
            return obj._meta.model_name
        else:
            return None

    async def get_context_data(self, **kwargs):
        """Insert the single object into the context dict."""
        context = {}
        if self.object:
            context["object"] = self.object
            context_object_name = self.get_context_object_name(self.object)
            if context_object_name:
                context[context_object_name] = self.object
        context.update(kwargs)
        return await super().get_context_data(**context)


class AsyncBaseDetailView(AsyncSingleObjectMixin, AsyncView):
    """
    Base view for displaying a single object.

    This requires subclassing to provide a response mixin.
    """

    async def get(self, request, *args, **kwargs):
        self.object = await self.get_object()
        context = await self.get_context_data(object=self.object)
        return await self.render_to_response(context)


class AsyncSingleObjectTemplateResponseMixin(AsyncTemplateResponseMixin):
    template_name_field = None
    template_name_suffix = "_detail"

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. May not be
        called if render_to_response() is overridden. Return the following list:

        * the value of ``template_name`` on the view (if provided)
        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * ``<app_label>/<model_name><template_name_suffix>.html``
        """
        try:
            names = super().get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

            # If self.template_name_field is set, grab the value of the field
            # of that name from the object; this is the most specific template
            # name, if given.
            if self.object and self.template_name_field:
                name = getattr(self.object, self.template_name_field, None)
                if name:
                    names.insert(0, name)

            # The least-specific option is the default <app>/<model>_detail.html;
            # only use this if the object in question is a model.
            if isinstance(self.object, models.Model):
                object_meta = self.object._meta
                names.append(
                    "%s/%s%s.html"
                    % (
                        object_meta.app_label,
                        object_meta.model_name,
                        self.template_name_suffix,
                    )
                )
            elif getattr(self, "model", None) is not None and issubclass(
                self.model, models.Model
            ):
                names.append(
                    "%s/%s%s.html"
                    % (
                        self.model._meta.app_label,
                        self.model._meta.model_name,
                        self.template_name_suffix,
                    )
                )

            # If we still haven't managed to find any template names, we should
            # re-raise the ImproperlyConfigured to alert the user.
            if not names:
                raise

        return names


class AsyncDetailView(AsyncSingleObjectTemplateResponseMixin, AsyncBaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """
