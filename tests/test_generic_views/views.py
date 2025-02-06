from django.urls import reverse_lazy

from django_async_extensions.aviews import generic

from .forms import ContactForm
from .models import Artist, Author, Page, Book


class CustomTemplateView(generic.AsyncTemplateView):
    template_name = "test_generic_views/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"key": "value"})
        return context


class ObjectDetail(generic.AsyncDetailView):
    template_name = "test_generic_views/detail.html"

    async def get_object(self):
        return {"foo": "bar"}


class ArtistDetail(generic.AsyncDetailView):
    queryset = Artist.objects.all()


class AuthorDetail(generic.AsyncDetailView):
    queryset = Author.objects.all()


class AuthorCustomDetail(generic.AsyncDetailView):
    template_name = "test_generic_views/author_detail.html"
    queryset = Author.objects.all()

    async def get(self, request, *args, **kwargs):
        # Ensures get_context_object_name() doesn't reference self.object.
        author = await self.get_object()
        context = {"custom_" + self.get_context_object_name(author): author}
        return self.render_to_response(context)


class PageDetail(generic.AsyncDetailView):
    queryset = Page.objects.all()
    template_name_field = "template"


class CustomContextView(generic.detail.AsyncSingleObjectMixin, generic.AsyncView):
    model = Book
    object = Book(name="dummy")

    async def get_object(self):
        return Book(name="dummy")

    def get_context_data(self, **kwargs):
        context = {"custom_key": "custom_value"}
        context.update(kwargs)
        return super().get_context_data(**context)

    def get_context_object_name(self, obj):
        return "test_name"


class CustomSingleObjectView(generic.detail.AsyncSingleObjectMixin, generic.AsyncView):
    model = Book
    object = Book(name="dummy")


class NonModel:
    id = "non_model_1"

    _meta = None


class NonModelDetail(generic.AsyncDetailView):
    template_name = "test_generic_views/detail.html"
    model = NonModel

    async def get_object(self, queryset=None):
        return NonModel()


class ObjectDoesNotExistDetail(generic.AsyncDetailView):
    async def get_queryset(self):
        return Book.does_not_exist.all()


class ContactView(generic.AsyncFormView):
    form_class = ContactForm
    success_url = reverse_lazy("authors_list")
    template_name = "test_generic_views/form.html"


class LateValidationView(generic.AsyncFormView):
    form_class = ContactForm
    success_url = reverse_lazy("authors_list")
    template_name = "test_generic_views/form.html"

    async def form_valid(self, form):
        form.add_error(None, "There is an error")
        return await self.form_invalid(form)


class AuthorGetQuerySetFormView(generic.edit.AsyncModelFormMixin):
    fields = "__all__"

    async def get_queryset(self):
        return Author.objects.all()
