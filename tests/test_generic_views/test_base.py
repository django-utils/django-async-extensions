import pathlib
import re
import time

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, Client
from django.urls import resolve

import pytest

from django_async_extensions.aviews.generic import (
    AsyncView,
    AsyncTemplateView,
    AsyncRedirectView,
)

try:
    import jinja2
except ImportError:
    jinja2 = None


TEMPLATE_DIR = pathlib.Path(__file__).parent.parent / "templates"

client = Client()


class SimpleView(AsyncView):
    """
    A simple view with a docstring.
    """

    async def get(self, request):
        return HttpResponse("This is a simple view")


class SimplePostView(SimpleView):
    post = SimpleView.get


class PostOnlyView(AsyncView):
    async def post(self, request):
        return HttpResponse("This view only accepts POST")


class CustomizableView(SimpleView):
    parameter = {}


def decorator(view):
    view.is_decorated = True
    return view


class DecoratedDispatchView(SimpleView):
    @decorator
    async def dispatch(self, request, *args, **kwargs):
        return await super().dispatch(request, *args, **kwargs)


class AboutTemplateView(AsyncTemplateView):
    async def get(self, request):
        return await self.render_to_response({})

    def get_template_names(self):
        return ["test_generic_views/about.html"]


class AboutTemplateAttributeView(AsyncTemplateView):
    template_name = "test_generic_views/about.html"

    async def get(self, request):
        return await self.render_to_response(context={})


class InstanceView(AsyncView):
    async def get(self, request):
        return self


class TestAsyncView:
    rf = RequestFactory()

    def _assert_simple(self, response):
        assert response.status_code == 200
        assert response.content == b"This is a simple view"

    async def test_no_init_kwargs(self):
        """
        A view can't be accidentally instantiated before deployment
        """
        msg = "This method is available only on the class, not on instances."
        with pytest.raises(AttributeError, match=msg):
            await SimpleView(key="value").as_view()

    async def test_no_init_args(self):
        """
        A view can't be accidentally instantiated before deployment
        """
        msg = "AsyncView.as_view() takes 1 positional argument but 2 were given"
        with pytest.raises(TypeError, match=re.escape(msg)):
            await SimpleView.as_view("value")

    async def test_pathological_http_method(self):
        """
        The edge case of an HTTP request that spoofs an existing method name is
        caught.
        """
        result = await SimpleView.as_view()(self.rf.get("/", REQUEST_METHOD="DISPATCH"))
        assert result.status_code == 405

    async def test_get_only(self):
        """
        Test a view which only allows GET doesn't allow other methods.
        """
        self._assert_simple(await SimpleView.as_view()(self.rf.get("/")))
        response = await SimpleView.as_view()(self.rf.post("/"))
        assert response.status_code == 405
        response = await SimpleView.as_view()(self.rf.get("/", REQUEST_METHOD="FAKE"))
        assert response.status_code == 405

    async def test_get_and_head(self):
        """
        Test a view which supplies a GET method also responds correctly to HEAD.
        """
        self._assert_simple(await SimpleView.as_view()(self.rf.get("/")))
        response = await SimpleView.as_view()(self.rf.head("/"))
        assert response.status_code == 200

    def test_setup_get_and_head(self):
        view_instance = SimpleView()
        assert not hasattr(view_instance, "head")
        view_instance.setup(self.rf.get("/"))
        assert hasattr(view_instance, "head")
        assert view_instance.head == view_instance.get

    async def test_head_no_get(self):
        """
        Test a view which supplies no GET method responds to HEAD with HTTP 405.
        """
        response = await PostOnlyView.as_view()(self.rf.head("/"))
        assert response.status_code == 405

    async def test_get_and_post(self):
        """
        Test a view which only allows both GET and POST.
        """
        self._assert_simple(await SimplePostView.as_view()(self.rf.get("/")))
        self._assert_simple(await SimplePostView.as_view()(self.rf.post("/")))
        response = await SimpleView.as_view()(self.rf.get("/", REQUEST_METHOD="FAKE"))
        assert response.status_code == 405

    async def test_invalid_keyword_argument(self):
        """
        View arguments must be predefined on the class and can't
        be named like an HTTP method.
        """
        msg = (
            "The method name %s is not accepted as a keyword argument to "
            "SimpleView()."
        )
        # Check each of the allowed method names
        for method in SimpleView.http_method_names:
            with pytest.raises(TypeError, match=re.escape(msg % method)):
                SimpleView.as_view(**{method: "value"})()

        # Check the case view argument is ok if predefined on the class...
        CustomizableView.as_view(parameter="value")
        # ...but raises errors otherwise.
        msg = re.escape(
            "CustomizableView() received an invalid keyword 'foobar'. "
            "as_view only accepts arguments that are already attributes of "
            "the class."
        )
        with pytest.raises(TypeError, match=msg):
            CustomizableView.as_view(foobar="value")()

    async def test_calling_more_than_once(self):
        """
        Test a view can only be called once.
        """
        request = self.rf.get("/")
        view = InstanceView.as_view()
        assert not await view(request) == await view(request)

    def test_class_attributes(self):
        """
        The callable returned from as_view() has proper special attributes.
        """
        cls = SimpleView
        view = cls.as_view()
        assert view.__doc__ == cls.__doc__
        assert view.__name__ == "view"
        assert view.__module__ == cls.__module__
        assert view.__qualname__ == f"{cls.as_view.__qualname__}.<locals>.view"
        assert view.__annotations__ == cls.dispatch.__annotations__
        assert not hasattr(view, "__wrapped__")

    def test_dispatch_decoration(self):
        """
        Attributes set by decorators on the dispatch method
        are also present on the closure.
        """
        assert DecoratedDispatchView.as_view().is_decorated

    async def test_options(self):
        """
        Views respond to HTTP OPTIONS requests with an Allow header
        appropriate for the methods implemented by the view class.
        """
        request = self.rf.options("/")
        view = SimpleView.as_view()
        response = await view(request)
        assert 200 == response.status_code
        assert response.headers["Allow"]

    async def test_options_for_get_view(self):
        """
        A view implementing GET allows GET and HEAD.
        """
        request = self.rf.options("/")
        view = SimpleView.as_view()
        response = await view(request)
        self._assert_allows(response, "GET", "HEAD")

    async def test_options_for_get_and_post_view(self):
        """
        A view implementing GET and POST allows GET, HEAD, and POST.
        """
        request = self.rf.options("/")
        view = SimplePostView.as_view()
        response = await view(request)
        self._assert_allows(response, "GET", "HEAD", "POST")

    async def test_options_for_post_view(self):
        """
        A view implementing POST allows POST.
        """
        request = self.rf.options("/")
        view = PostOnlyView.as_view()
        response = await view(request)
        self._assert_allows(response, "POST")

    def _assert_allows(self, response, *expected_methods):
        "Assert allowed HTTP methods reported in the Allow response header"
        response_allows = set(response.headers["Allow"].split(", "))
        assert set(expected_methods + ("OPTIONS",)) == response_allows

    async def test_args_kwargs_request_on_self(self):
        """
        Test a view only has args, kwargs & request once `as_view`
        has been called.
        """
        bare_view = InstanceView()
        view = await InstanceView.as_view()(self.rf.get("/"))
        for attribute in ("args", "kwargs", "request"):
            assert attribute not in dir(bare_view)
            assert attribute in dir(view)

    async def test_overridden_setup(self):
        class SetAttributeMixin:
            def setup(self, request, *args, **kwargs):
                self.attr = True
                super().setup(request, *args, **kwargs)

        class CheckSetupView(SetAttributeMixin, SimpleView):
            async def dispatch(self, request, *args, **kwargs):
                assert hasattr(self, "attr")
                return await super().dispatch(request, *args, **kwargs)

        response = await CheckSetupView.as_view()(self.rf.get("/"))
        assert response.status_code == 200

    async def test_not_calling_parent_setup_error(self):
        class TestView(AsyncView):
            def setup(self, request, *args, **kwargs):
                pass  # Not calling super().setup()

        msg = re.escape(
            "TestView instance has no 'request' attribute. Did you override "
            "setup() and forgot to call super()?"
        )
        with pytest.raises(AttributeError, match=msg):
            await TestView.as_view()(self.rf.get("/"))

    def test_setup_adds_args_kwargs_request(self):
        request = self.rf.get("/")
        args = ("arg 1", "arg 2")
        kwargs = {"kwarg_1": 1, "kwarg_2": "year"}

        view = AsyncView()
        view.setup(request, *args, **kwargs)
        assert request == view.request
        assert args == view.args
        assert kwargs == view.kwargs

    async def test_direct_instantiation(self):
        """
        It should be possible to use the view by directly instantiating it
        without going through .as_view() (#21564).
        """
        view = PostOnlyView()
        response = await view.dispatch(self.rf.head("/"))
        assert response.status_code == 405


@pytest.fixture(autouse=True)
def urlconf_setting_set(settings):
    old_urlconf = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "test_generic_views.urls"
    yield settings
    settings.ROOT_URLCONF = old_urlconf


class TestAsyncTemplateView:
    rf = RequestFactory()

    def _assert_about(self, response):
        response.render()
        assert b"<h1>About</h1>" in response.content

    async def test_get(self):
        """
        Test a view that simply renders a template on GET
        """
        self._assert_about(await AboutTemplateView.as_view()(self.rf.get("/about/")))

    async def test_head(self):
        """
        Test a TemplateView responds correctly to HEAD
        """
        response = await AboutTemplateView.as_view()(self.rf.head("/about/"))
        assert response.status_code == 200

    async def test_get_template_attribute(self):
        """
        Test a view that renders a template on GET with the template name as
        an attribute on the class.
        """
        self._assert_about(
            await AboutTemplateAttributeView.as_view()(self.rf.get("/about/"))
        )

    async def test_get_generic_template(self):
        """
        Test a completely generic view that renders a template on GET
        with the template name as an argument at instantiation.
        """
        self._assert_about(
            await AsyncTemplateView.as_view(
                template_name="test_generic_views/about.html"
            )(self.rf.get("/about/"))
        )

    def test_template_name_required(self):
        """
        A template view must provide a template name.
        """
        msg = re.escape(
            "TemplateResponseMixin requires either a definition of "
            "'template_name' or an implementation of 'get_template_names()'"
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/template/no_template/")

    @pytest.mark.skipif(jinja2 is None, reason="this test requires jinja2")
    async def test_template_engine(self, settings):
        """
        A template view may provide a template engine.
        """
        settings.TEMPLATES = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [TEMPLATE_DIR],
                "APP_DIRS": True,
            },
            {
                "BACKEND": "django.template.backends.jinja2.Jinja2",
                "APP_DIRS": True,
                "OPTIONS": {"keep_trailing_newline": True},
            },
        ]

        request = self.rf.get("/using/")
        view = AsyncTemplateView.as_view(template_name="test_generic_views/using.html")
        view = await view(request)
        assert view.render().content == b"DTL\n"
        view = AsyncTemplateView.as_view(
            template_name="test_generic_views/using.html", template_engine="django"
        )
        view = await view(request)
        assert view.render().content == b"DTL\n"
        view = AsyncTemplateView.as_view(
            template_name="test_generic_views/using.html", template_engine="jinja2"
        )
        view = await view(request)
        assert view.render().content == b"Jinja2\n"

    def test_template_params(self):
        """
        A generic template view passes kwargs as context.
        """
        response = client.get("/template/simple/bar/")
        assert response.status_code == 200
        assert response.context["foo"] == "bar"
        assert isinstance(response.context["view"], AsyncView)

    def test_extra_template_params(self):
        """
        A template view can be customized to return extra context.
        """
        response = client.get("/template/custom/bar/")
        assert response.status_code == 200
        assert response.context["foo"] == "bar"
        assert response.context["key"] == "value"
        assert isinstance(response.context["view"], AsyncView)

    def test_cached_views(self):
        """
        A template view can be cached
        """
        response = client.get("/template/cached/bar/")
        assert response.status_code == 200

        time.sleep(1.0)

        response2 = client.get("/template/cached/bar/")
        assert response2.status_code == 200

        assert response.content == response2.content

        time.sleep(2.0)

        # Let the cache expire and test again
        response2 = client.get("/template/cached/bar/")
        assert response2.status_code == 200

        assert not response.content == response2.content

    def test_content_type(self):
        response = client.get("/template/content_type/")
        assert response.headers["Content-Type"] == "text/plain"

    def test_resolve_view(self):
        match = resolve("/template/content_type/")
        assert match.func.view_class is AsyncTemplateView
        assert match.func.view_initkwargs["content_type"] == "text/plain"

    def test_resolve_login_required_view(self):
        match = resolve("/template/login_required/")
        assert match.func.view_class is AsyncTemplateView

    def test_extra_context(self):
        response = client.get("/template/extra_context/")
        assert response.context["title"] == "Title"


class TestAsyncRedirectView:
    rf = RequestFactory()

    async def test_no_url(self):
        "Without any configuration, returns HTTP 410 GONE"
        response = await AsyncRedirectView.as_view()(self.rf.get("/foo/"))
        assert response.status_code == 410

    async def test_default_redirect(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.get("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_permanent_redirect(self):
        "Permanent redirects are an option"
        response = await AsyncRedirectView.as_view(url="/bar/", permanent=True)(
            self.rf.get("/foo/")
        )
        assert response.status_code == 301
        assert response.url == "/bar/"

    async def test_temporary_redirect(self):
        "Temporary redirects are an option"
        response = await AsyncRedirectView.as_view(url="/bar/", permanent=False)(
            self.rf.get("/foo/")
        )
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_include_args(self):
        "GET arguments can be included in the redirected URL"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.get("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

        response = await AsyncRedirectView.as_view(url="/bar/", query_string=True)(
            self.rf.get("/foo/?pork=spam")
        )
        assert response.status_code == 302
        assert response.url == "/bar/?pork=spam"

    async def test_include_urlencoded_args(self):
        "GET arguments can be URL-encoded when included in the redirected URL"
        response = await AsyncRedirectView.as_view(url="/bar/", query_string=True)(
            self.rf.get("/foo/?unicode=%E2%9C%93")
        )
        assert response.status_code == 302
        assert response.url == "/bar/?unicode=%E2%9C%93"

    async def test_parameter_substitution(self):
        "Redirection URLs can be parameterized"
        response = await AsyncRedirectView.as_view(url="/bar/%(object_id)d/")(
            self.rf.get("/foo/42/"), object_id=42
        )
        assert response.status_code == 302
        assert response.url == "/bar/42/"

    async def test_named_url_pattern(self):
        "Named pattern parameter should reverse to the matching pattern"
        response = await AsyncRedirectView.as_view(pattern_name="artist_detail")(
            self.rf.get("/foo/"), pk=1
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "/detail/artist/1/"

    async def test_named_url_pattern_using_args(self):
        response = await AsyncRedirectView.as_view(pattern_name="artist_detail")(
            self.rf.get("/foo/"), 1
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "/detail/artist/1/"

    async def test_redirect_POST(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.post("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_HEAD(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.head("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_OPTIONS(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(
            self.rf.options("/foo/")
        )
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_PUT(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.put("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_PATCH(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.patch("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_DELETE(self):
        "Default is a temporary redirect"
        response = await AsyncRedirectView.as_view(url="/bar/")(self.rf.delete("/foo/"))
        assert response.status_code == 302
        assert response.url == "/bar/"

    async def test_redirect_when_meta_contains_no_query_string(self):
        "regression for #16705"
        # we can't use self.rf.get because it always sets QUERY_STRING
        response = await AsyncRedirectView.as_view(url="/bar/")(
            self.rf.request(PATH_INFO="/foo/")
        )
        assert response.status_code == 302

    async def test_direct_instantiation(self):
        """
        It should be possible to use the view without going through .as_view()
        (#21564).
        """
        view = AsyncRedirectView()
        response = await view.dispatch(self.rf.head("/foo/"))
        assert response.status_code == 410
