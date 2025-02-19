# note on these tests:
# there are more tests here than currently needed
# the reason is, i plan to add much more tools to `AsyncModelForm`
# and as development goes on, i want to be sure nothing breaks.
import datetime
import os
import re
import shutil
from decimal import Decimal
from unittest import mock

import pytest
from asgiref.sync import sync_to_async
from pytest_django.asserts import assertNumQueries, assertHTMLEqual

from django import forms
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    FieldError,
    ImproperlyConfigured,
    ValidationError,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, models
from django.db.models.query import EmptyQuerySet
from django.forms.models import (
    ModelFormMetaclass,
    construct_instance,
    fields_for_model,
    model_to_dict,
    modelform_factory,
)
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps
from django.utils.choices import BlankChoiceIterator
from django.utils.version import PYPY

from django_async_extensions.aforms.models import AsyncModelForm

from .models import (
    Article,
    ArticleStatus,
    Author,
    Author1,
    Award,
    BetterWriter,
    BigInt,
    Book,
    Category,
    Character,
    Colour,
    ColourfulItem,
    CustomErrorMessage,
    CustomFF,
    CustomFieldForExclusionModel,
    DateTimePost,
    DerivedBook,
    DerivedPost,
    Dice,
    Document,
    ExplicitPK,
    FilePathModel,
    FlexibleDatePost,
    Homepage,
    ImprovedArticle,
    ImprovedArticleWithParentLink,
    Inventory,
    NullableUniqueCharFieldModel,
    Number,
    Person,
    Photo,
    Post,
    Price,
    Product,
    Publication,
    PublicationDefaults,
    StrictAssignmentAll,
    StrictAssignmentFieldSpecific,
    Student,
    StumpJoke,
    TextFile,
    Triple,
    Writer,
    WriterProfile,
    temp_storage_dir,
    test_images,
)

if test_images:
    from .models import ImageFile, NoExtensionImageFile, OptionalImageFile

    class ImageFileForm(AsyncModelForm):
        class Meta:
            model = ImageFile
            fields = "__all__"

    class OptionalImageFileForm(AsyncModelForm):
        class Meta:
            model = OptionalImageFile
            fields = "__all__"

    class NoExtensionImageFileForm(AsyncModelForm):
        class Meta:
            model = NoExtensionImageFile
            fields = "__all__"


class ProductForm(AsyncModelForm):
    class Meta:
        model = Product
        fields = "__all__"


class PriceForm(AsyncModelForm):
    class Meta:
        model = Price
        fields = "__all__"


class BookForm(AsyncModelForm):
    class Meta:
        model = Book
        fields = "__all__"


class DerivedBookForm(AsyncModelForm):
    class Meta:
        model = DerivedBook
        fields = "__all__"


class ExplicitPKForm(AsyncModelForm):
    class Meta:
        model = ExplicitPK
        fields = (
            "key",
            "desc",
        )


class PostForm(AsyncModelForm):
    class Meta:
        model = Post
        fields = "__all__"


class DerivedPostForm(AsyncModelForm):
    class Meta:
        model = DerivedPost
        fields = "__all__"


class CustomWriterForm(AsyncModelForm):
    name = forms.CharField(required=False)

    class Meta:
        model = Writer
        fields = "__all__"


class BaseCategoryForm(AsyncModelForm):
    class Meta:
        model = Category
        fields = "__all__"


class ArticleForm(AsyncModelForm):
    class Meta:
        model = Article
        fields = "__all__"


class RoykoForm(AsyncModelForm):
    class Meta:
        model = Writer
        fields = "__all__"


class ArticleStatusForm(AsyncModelForm):
    class Meta:
        model = ArticleStatus
        fields = "__all__"


class InventoryForm(AsyncModelForm):
    class Meta:
        model = Inventory
        fields = "__all__"


class SelectInventoryForm(forms.Form):
    items = forms.ModelMultipleChoiceField(
        Inventory.objects.all(), to_field_name="barcode"
    )


class CustomFieldForExclusionForm(AsyncModelForm):
    class Meta:
        model = CustomFieldForExclusionModel
        fields = ["name", "markup"]


class TextFileForm(AsyncModelForm):
    class Meta:
        model = TextFile
        fields = "__all__"


class BigIntForm(AsyncModelForm):
    class Meta:
        model = BigInt
        fields = "__all__"


class ModelFormWithMedia(AsyncModelForm):
    class Media:
        js = ("/some/form/javascript",)
        css = {"all": ("/some/form/css",)}

    class Meta:
        model = TextFile
        fields = "__all__"


class CustomErrorMessageForm(AsyncModelForm):
    name1 = forms.CharField(error_messages={"invalid": "Form custom error message."})

    class Meta:
        fields = "__all__"
        model = CustomErrorMessage


@pytest.mark.django_db(transaction=True)
class TestModelFormBase:
    def test_base_form(self):
        assert list(BaseCategoryForm.base_fields) == ["name", "slug", "url"]

    def test_no_model_class(self):
        class NoModelModelForm(AsyncModelForm):
            pass

        with pytest.raises(ValueError, match="ModelForm has no model class specified."):
            NoModelModelForm()

    def test_empty_fields_to_fields_for_model(self):
        """
        An argument of fields=() to fields_for_model should return an empty dictionary
        """
        field_dict = fields_for_model(Person, fields=())
        assert len(field_dict) == 0

    def test_fields_for_model_form_fields(self):
        form_declared_fields = CustomWriterForm.declared_fields
        field_dict = fields_for_model(
            Writer,
            fields=["name"],
            form_declared_fields=form_declared_fields,
        )
        assert field_dict["name"] == form_declared_fields["name"]

    def test_empty_fields_on_modelform(self):
        """
        No fields on a ModelForm should actually result in no fields.
        """

        class EmptyPersonForm(AsyncModelForm):
            class Meta:
                model = Person
                fields = ()

        form = EmptyPersonForm()
        assert len(form.fields) == 0

    def test_empty_fields_to_construct_instance(self):
        """
        No fields should be set on a model instance if construct_instance
        receives fields=().
        """
        form = modelform_factory(Person, fields="__all__", form=AsyncModelForm)(
            {"name": "John Doe"}
        )
        assert form.is_valid()
        instance = construct_instance(form, Person(), fields=())
        assert instance.name == ""

    async def test_blank_with_null_foreign_key_field(self):
        """
        #13776 -- ModelForm's with models having a FK set to null=False and
        required=False should be valid.
        """

        class FormForTestingIsValid(AsyncModelForm):
            class Meta:
                model = Student
                fields = "__all__"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields["character"].required = False

        char = await Character.objects.acreate(
            username="user", last_action=datetime.datetime.today()
        )
        data = {"study": "Engineering"}
        data2 = {"study": "Engineering", "character": char.pk}

        # form is valid because required=False for field 'character'
        f1 = FormForTestingIsValid(data)
        assert f1.is_valid()

        f2 = FormForTestingIsValid(data2)
        assert await sync_to_async(f2.is_valid)()

        obj = await f2.asave()
        assert obj.character == char

    async def test_blank_false_with_null_true_foreign_key_field(self):
        """
        A ModelForm with a model having ForeignKey(blank=False, null=True)
        and the form field set to required=False should allow the field to be
        unset.
        """

        class AwardForm(AsyncModelForm):
            class Meta:
                model = Award
                fields = "__all__"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields["character"].required = False

        character = await Character.objects.acreate(
            username="user", last_action=datetime.datetime.today()
        )
        award = await Award.objects.acreate(name="Best sprinter", character=character)
        data = {"name": "Best tester", "character": ""}  # remove character
        form = AwardForm(data=data, instance=award)
        assert form.is_valid()
        award = await form.asave()
        assert award.character is None

    def test_blank_foreign_key_with_radio(self):
        class BookForm(AsyncModelForm):
            class Meta:
                model = Book
                fields = ["author"]
                widgets = {"author": forms.RadioSelect()}

        writer = Writer.objects.create(name="Joe Doe")
        form = BookForm()
        assert list(form.fields["author"].choices) == [
            ("", "---------"),
            (writer.pk, "Joe Doe"),
        ]

    def test_non_blank_foreign_key_with_radio(self):
        class AwardForm(AsyncModelForm):
            class Meta:
                model = Award
                fields = ["character"]
                widgets = {"character": forms.RadioSelect()}

        character = Character.objects.create(
            username="user",
            last_action=datetime.datetime.today(),
        )
        form = AwardForm()
        assert list(form.fields["character"].choices) == [(character.pk, "user")]

    async def test_save_blank_false_with_required_false(self):
        """
        A ModelForm with a model with a field set to blank=False and the form
        field set to required=False should allow the field to be unset.
        """
        obj = await Writer.objects.acreate(name="test")
        form = CustomWriterForm(data={"name": ""}, instance=obj)
        assert form.is_valid()
        obj = await form.asave()
        assert obj.name == ""

    async def test_save_blank_null_unique_charfield_saves_null(self):
        form_class = modelform_factory(
            model=NullableUniqueCharFieldModel, fields="__all__", form=AsyncModelForm
        )
        empty_value = (
            "" if connection.features.interprets_empty_strings_as_nulls else None
        )
        data = {
            "codename": "",
            "email": "",
            "slug": "",
            "url": "",
        }
        form = form_class(data=data)
        assert form.is_valid()
        await form.asave()
        assert form.instance.codename == empty_value
        assert form.instance.email == empty_value
        assert form.instance.slug == empty_value
        assert form.instance.url == empty_value

        # Save a second form to verify there isn't a unique constraint violation.
        form = form_class(data=data)
        assert form.is_valid()
        await form.asave()
        assert form.instance.codename == empty_value
        assert form.instance.email == empty_value
        assert form.instance.slug == empty_value
        assert form.instance.url == empty_value

    def test_missing_fields_attribute(self):
        message = (
            "Creating a ModelForm without either the 'fields' attribute "
            "or the 'exclude' attribute is prohibited; form "
            "MissingFieldsForm needs updating."
        )
        with pytest.raises(ImproperlyConfigured, match=message):

            class MissingFieldsForm(AsyncModelForm):
                class Meta:
                    model = Category

    def test_extra_fields(self):
        class ExtraFields(BaseCategoryForm):
            some_extra_field = forms.BooleanField()

        assert list(ExtraFields.base_fields) == [
            "name",
            "slug",
            "url",
            "some_extra_field",
        ]

    def test_extra_field_model_form(self):
        with pytest.raises(FieldError, match=re.escape("no-field")):

            class ExtraPersonForm(AsyncModelForm):
                """ModelForm with an extra field"""

                age = forms.IntegerField()

                class Meta:
                    model = Person
                    fields = ("name", "no-field")

    def test_extra_declared_field_model_form(self):
        class ExtraPersonForm(AsyncModelForm):
            """ModelForm with an extra field"""

            age = forms.IntegerField()

            class Meta:
                model = Person
                fields = ("name", "age")

    def test_extra_field_modelform_factory(self):
        with pytest.raises(
            FieldError,
            match=re.escape("Unknown field(s) (no-field) specified for Person"),
        ):
            modelform_factory(Person, fields=["no-field", "name"], form=AsyncModelForm)

    def test_replace_field(self):
        class ReplaceField(AsyncModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category
                fields = "__all__"

        assert isinstance(ReplaceField.base_fields["url"], forms.fields.BooleanField)

    def test_replace_field_variant_2(self):
        # Should have the same result as before,
        # but 'fields' attribute specified differently
        class ReplaceField(AsyncModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category
                fields = ["url"]

        assert isinstance(ReplaceField.base_fields["url"], forms.fields.BooleanField)

    def test_replace_field_variant_3(self):
        # Should have the same result as before,
        # but 'fields' attribute specified differently
        class ReplaceField(AsyncModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category
                fields = []  # url will still appear, since it is explicit above

        assert isinstance(ReplaceField.base_fields["url"], forms.fields.BooleanField)

    def test_override_field(self):
        class WriterForm(AsyncModelForm):
            book = forms.CharField(required=False)

            class Meta:
                model = Writer
                fields = "__all__"

        wf = WriterForm({"name": "Richard Lockridge"})
        assert wf.is_valid()

    def test_limit_nonexistent_field(self):
        expected_msg = re.escape(
            "Unknown field(s) (nonexistent) specified for Category"
        )
        with pytest.raises(FieldError, match=expected_msg):

            class InvalidCategoryForm(AsyncModelForm):
                class Meta:
                    model = Category
                    fields = ["nonexistent"]

    def test_limit_fields_with_string(self):
        msg = (
            "CategoryForm.Meta.fields cannot be a string. Did you mean to type: "
            "('url',)?"
        )
        with pytest.raises(TypeError, match=msg):

            class CategoryForm(AsyncModelForm):
                class Meta:
                    model = Category
                    fields = "url"  # note the missing comma

    def test_exclude_fields(self):
        class ExcludeFields(AsyncModelForm):
            class Meta:
                model = Category
                exclude = ["url"]

        assert list(ExcludeFields.base_fields) == ["name", "slug"]

    def test_exclude_nonexistent_field(self):
        class ExcludeFields(AsyncModelForm):
            class Meta:
                model = Category
                exclude = ["nonexistent"]

        assert list(ExcludeFields.base_fields) == ["name", "slug", "url"]

    def test_exclude_fields_with_string(self):
        msg = (
            "CategoryForm.Meta.exclude cannot be a string. Did you mean to type: "
            "('url',)?"
        )
        with pytest.raises(TypeError, match=msg):

            class CategoryForm(AsyncModelForm):
                class Meta:
                    model = Category
                    exclude = "url"  # note the missing comma

    async def test_exclude_and_validation(self):
        # This Price instance generated by this form is not valid because the quantity
        # field is required, but the form is valid because the field is excluded from
        # the form. This is for backwards compatibility.
        class PriceFormWithoutQuantity(AsyncModelForm):
            class Meta:
                model = Price
                exclude = ("quantity",)

        form = PriceFormWithoutQuantity({"price": "6.00"})
        assert form.is_valid()
        price = await form.asave(commit=False)
        msg = re.escape("{'quantity': ['This field cannot be null.']}")
        with pytest.raises(ValidationError, match=msg):
            price.full_clean()

        # The form should not validate fields that it doesn't contain even if they are
        # specified using 'fields', not 'exclude'.
        class PriceFormWithoutQuantity(AsyncModelForm):
            class Meta:
                model = Price
                fields = ("price",)

        form = PriceFormWithoutQuantity({"price": "6.00"})
        assert form.is_valid()

        # The form should still have an instance of a model that is not complete and
        # not saved into a DB yet.
        assert form.instance.price == Decimal("6.00")
        assert form.instance.quantity is None
        assert form.instance.pk is None

    def test_confused_form(self):
        class ConfusedForm(AsyncModelForm):
            """Using 'fields' *and* 'exclude'. Not sure why you'd want to do
            this, but uh, "be liberal in what you accept" and all.
            """

            class Meta:
                model = Category
                fields = ["name", "url"]
                exclude = ["url"]

        assert list(ConfusedForm.base_fields) == ["name"]

    def test_mixmodel_form(self):
        class MixModelForm(BaseCategoryForm):
            """Don't allow more than one 'model' definition in the
            inheritance hierarchy.  Technically, it would generate a valid
            form, but the fact that the resulting save method won't deal with
            multiple objects is likely to trip up people not familiar with the
            mechanics.
            """

            class Meta:
                model = Article
                fields = "__all__"

            # MixModelForm is now an Article-related thing, because MixModelForm.Meta
            # overrides BaseCategoryForm.Meta.

        assert list(MixModelForm.base_fields) == [
            "headline",
            "slug",
            "pub_date",
            "writer",
            "article",
            "categories",
            "status",
        ]

    def test_article_form(self):
        assert list(ArticleForm.base_fields) == [
            "headline",
            "slug",
            "pub_date",
            "writer",
            "article",
            "categories",
            "status",
        ]

    def test_bad_form(self):
        # First class with a Meta class wins...
        class BadForm(ArticleForm, BaseCategoryForm):
            pass

        assert list(BadForm.base_fields) == [
            "headline",
            "slug",
            "pub_date",
            "writer",
            "article",
            "categories",
            "status",
        ]

    def test_invalid_meta_model(self):
        class InvalidModelForm(AsyncModelForm):
            class Meta:
                pass  # no model

        # Can't create new form
        msg = "ModelForm has no model class specified."
        with pytest.raises(ValueError, match=msg):
            InvalidModelForm()

        # Even if you provide a model instance
        with pytest.raises(ValueError, match=msg):
            InvalidModelForm(instance=Category)

    def test_subcategory_form(self):
        class SubCategoryForm(BaseCategoryForm):
            """Subclassing without specifying a Meta on the class will use
            the parent's Meta (or the first parent in the MRO if there are
            multiple parent classes).
            """

            pass

        assert list(SubCategoryForm.base_fields) == ["name", "slug", "url"]

    def test_subclassmeta_form(self):
        class SomeCategoryForm(AsyncModelForm):
            checkbox = forms.BooleanField()

            class Meta:
                model = Category
                fields = "__all__"

        class SubclassMeta(SomeCategoryForm):
            """We can also subclass the Meta inner class to change the fields
            list.
            """

            class Meta(SomeCategoryForm.Meta):
                exclude = ["url"]

        assertHTMLEqual(
            str(SubclassMeta()),
            '<div><label for="id_name">Name:</label>'
            '<input type="text" name="name" maxlength="20" required id="id_name">'
            '</div><div><label for="id_slug">Slug:</label><input type="text" '
            'name="slug" maxlength="20" required id="id_slug"></div><div>'
            '<label for="id_checkbox">Checkbox:</label>'
            '<input type="checkbox" name="checkbox" required id="id_checkbox"></div>',
        )

    def test_orderfields_form(self):
        class OrderFields(AsyncModelForm):
            class Meta:
                model = Category
                fields = ["url", "name"]

        assert list(OrderFields.base_fields) == ["url", "name"]
        assertHTMLEqual(
            str(OrderFields()),
            '<div><label for="id_url">The URL:</label>'
            '<input type="text" name="url" maxlength="40" required id="id_url">'
            '</div><div><label for="id_name">Name:</label><input type="text" '
            'name="name" maxlength="20" required id="id_name"></div>',
        )

    def test_orderfields2_form(self):
        class OrderFields2(AsyncModelForm):
            class Meta:
                model = Category
                fields = ["slug", "url", "name"]
                exclude = ["url"]

        assert list(OrderFields2.base_fields) == ["slug", "name"]

    async def test_default_populated_on_optional_field(self):
        class PubForm(AsyncModelForm):
            mode = forms.CharField(max_length=255, required=False)

            class Meta:
                model = PublicationDefaults
                fields = ("mode",)

        # Empty data uses the model field default.
        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.mode == "di"
        assert m1._meta.get_field("mode").get_default() == "di"

        # Blank data doesn't use the model field default.
        mf2 = PubForm({"mode": ""})
        assert mf2.errors == {}
        m2 = await mf2.asave(commit=False)
        assert m2.mode == ""

    async def test_default_not_populated_on_non_empty_value_in_cleaned_data(
        self, subtests
    ):
        class PubForm(AsyncModelForm):
            mode = forms.CharField(max_length=255, required=False)
            mocked_mode = None

            def clean(self):
                self.cleaned_data["mode"] = self.mocked_mode
                return self.cleaned_data

            class Meta:
                model = PublicationDefaults
                fields = ("mode",)

        pub_form = PubForm({})
        pub_form.mocked_mode = "de"
        pub = await pub_form.asave(commit=False)
        assert pub.mode == "de"
        # Default should be populated on an empty value in cleaned_data.
        default_mode = "di"
        for empty_value in pub_form.fields["mode"].empty_values:
            with subtests.test(empty_value=empty_value):
                pub_form = PubForm({})
                pub_form.mocked_mode = empty_value
                pub = await pub_form.asave(commit=False)
                assert pub.mode == default_mode

    async def test_default_not_populated_on_optional_checkbox_input(self):
        class PubForm(AsyncModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ("active",)

        # Empty data doesn't use the model default because CheckboxInput
        # doesn't have a value in HTML form submission.
        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.active is False
        assert isinstance(mf1.fields["active"].widget, forms.CheckboxInput)
        assert m1._meta.get_field("active").get_default() is True

    async def test_default_not_populated_on_checkboxselectmultiple(self):
        class PubForm(AsyncModelForm):
            mode = forms.CharField(required=False, widget=forms.CheckboxSelectMultiple)

            class Meta:
                model = PublicationDefaults
                fields = ("mode",)

        # Empty data doesn't use the model default because an unchecked
        # CheckboxSelectMultiple doesn't have a value in HTML form submission.
        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.mode == ""
        assert m1._meta.get_field("mode").get_default() == "di"

    async def test_default_not_populated_on_selectmultiple(self):
        class PubForm(AsyncModelForm):
            mode = forms.CharField(required=False, widget=forms.SelectMultiple)

            class Meta:
                model = PublicationDefaults
                fields = ("mode",)

        # Empty data doesn't use the model default because an unselected
        # SelectMultiple doesn't have a value in HTML form submission.
        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.mode == ""
        assert m1._meta.get_field("mode").get_default() == "di"

    async def test_prefixed_form_with_default_field(self):
        class PubForm(AsyncModelForm):
            prefix = "form-prefix"

            class Meta:
                model = PublicationDefaults
                fields = ("mode",)

        mode = "de"
        assert mode != PublicationDefaults._meta.get_field("mode").get_default()

        mf1 = PubForm({"form-prefix-mode": mode})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.mode == mode

    def test_renderer_kwarg(self):
        custom = object()
        assert ProductForm(renderer=custom).renderer is custom

    async def test_default_splitdatetime_field(self):
        class PubForm(AsyncModelForm):
            datetime_published = forms.SplitDateTimeField(required=False)

            class Meta:
                model = PublicationDefaults
                fields = ("datetime_published",)

        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.datetime_published == datetime.datetime(2000, 1, 1)

        mf2 = PubForm(
            {"datetime_published_0": "2010-01-01", "datetime_published_1": "0:00:00"}
        )
        assert mf2.errors == {}
        m2 = await mf2.asave(commit=False)
        assert m2.datetime_published == datetime.datetime(2010, 1, 1)

    async def test_default_filefield(self):
        class PubForm(AsyncModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ("file",)

        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.file.name == "default.txt"

        mf2 = PubForm({}, {"file": SimpleUploadedFile("name", b"foo")})
        assert mf2.errors == {}
        m2 = await mf2.asave(commit=False)
        assert m2.file.name == "name"

    async def test_default_selectdatewidget(self):
        class PubForm(AsyncModelForm):
            date_published = forms.DateField(
                required=False, widget=forms.SelectDateWidget
            )

            class Meta:
                model = PublicationDefaults
                fields = ("date_published",)

        mf1 = PubForm({})
        assert mf1.errors == {}
        m1 = await mf1.asave(commit=False)
        assert m1.date_published == datetime.date.today()

        mf2 = PubForm(
            {
                "date_published_year": "2010",
                "date_published_month": "1",
                "date_published_day": "1",
            }
        )
        assert mf2.errors == {}
        m2 = await mf2.asave(commit=False)
        assert m2.date_published == datetime.date(2010, 1, 1)


class IncompleteCategoryFormWithFields(AsyncModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """

    url = forms.CharField(required=False)

    class Meta:
        fields = ("name", "slug")
        model = Category


class IncompleteCategoryFormWithExclude(AsyncModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """

    url = forms.CharField(required=False)

    class Meta:
        exclude = ["url"]
        model = Category


class ValidationTest(SimpleTestCase):
    def test_validates_with_replaced_field_not_specified(self):
        form = IncompleteCategoryFormWithFields(
            data={"name": "some name", "slug": "some-slug"}
        )
        self.assertIs(form.is_valid(), True)

    def test_validates_with_replaced_field_excluded(self):
        form = IncompleteCategoryFormWithExclude(
            data={"name": "some name", "slug": "some-slug"}
        )
        self.assertIs(form.is_valid(), True)

    def test_notrequired_overrides_notblank(self):
        form = CustomWriterForm({})
        self.assertIs(form.is_valid(), True)


@pytest.mark.django_db(transaction=True)
class TestUnique:
    """
    unique/unique_together validation.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.writer = Writer.objects.create(name="Mike Royko")

    async def test_simple_unique(self):
        form = ProductForm({"slug": "teddy-bear-blue"})
        assert await sync_to_async(form.is_valid)()
        obj = await form.asave()
        form = ProductForm({"slug": "teddy-bear-blue"})
        await sync_to_async(form.full_clean)()
        assert len(form.errors) == 1
        assert form.errors["slug"] == ["Product with this Slug already exists."]
        form = ProductForm({"slug": "teddy-bear-blue"}, instance=obj)
        assert await sync_to_async(form.is_valid)()

    async def test_unique_together(self):
        """ModelForm test of unique_together constraint"""
        form = PriceForm({"price": "6.00", "quantity": "1"})
        assert await sync_to_async(form.is_valid)()
        await form.asave()
        form = PriceForm({"price": "6.00", "quantity": "1"})
        assert await sync_to_async(form.is_valid)() is False
        await sync_to_async(form.full_clean)()
        assert len(form.errors) == 1
        assert form.errors["__all__"] == [
            "Price with this Price and Quantity already exists."
        ]

    def test_unique_together_exclusion(self, subtests):
        """
        Forms don't validate unique_together constraints when only part of the
        constraint is included in the form's fields. This allows using
        form.save(commit=False) and then assigning the missing field(s) to the
        model instance.
        """

        class BookForm(AsyncModelForm):
            class Meta:
                model = DerivedBook
                fields = ("isbn", "suffix1")

        # The unique_together is on suffix1/suffix2 but only suffix1 is part
        # of the form. The fields must have defaults, otherwise they'll be
        # skipped by other logic.
        assert DerivedBook._meta.unique_together == (("suffix1", "suffix2"),)
        for name in ("suffix1", "suffix2"):
            with subtests.test(name=name):
                field = DerivedBook._meta.get_field(name)
                assert field.default == 0

        # The form fails validation with "Derived book with this Suffix1 and
        # Suffix2 already exists." if the unique_together validation isn't
        # skipped.
        DerivedBook.objects.create(isbn="12345")
        form = BookForm({"isbn": "56789", "suffix1": "0"})
        assert form.is_valid(), form.errors

    def test_multiple_field_unique_together(self):
        """
        When the same field is involved in multiple unique_together
        constraints, we need to make sure we don't remove the data for it
        before doing all the validation checking (not just failing after
        the first one).
        """

        class TripleForm(AsyncModelForm):
            class Meta:
                model = Triple
                fields = "__all__"

        Triple.objects.create(left=1, middle=2, right=3)

        form = TripleForm({"left": "1", "middle": "2", "right": "3"})
        assert form.is_valid() is False

        form = TripleForm({"left": "1", "middle": "3", "right": "1"})
        assert form.is_valid()

    @pytest.mark.skipif(
        not getattr(connection.features, "supports_nullable_unique_constraints", False),
        reason="Database doesn't support nullable unique constraints",
    )
    async def test_unique_null(self):
        title = "I May Be Wrong But I Doubt It"
        form = BookForm({"title": title, "author": self.writer.pk})
        assert await sync_to_async(form.is_valid)()
        await form.asave()
        form = BookForm({"title": title, "author": self.writer.pk})
        assert await sync_to_async(form.is_valid)() is False
        await sync_to_async(form.full_clean)()
        assert len(form.errors) == 1
        assert form.errors["__all__"] == [
            "Book with this Title and Author already exists."
        ]
        form = BookForm({"title": title})
        assert form.is_valid()
        await form.asave()
        form = BookForm({"title": title})
        assert form.is_valid()

    def test_inherited_unique(self):
        title = "Boss"
        Book.objects.create(title=title, author=self.writer, special_id=1)
        form = DerivedBookForm(
            {
                "title": "Other",
                "author": self.writer.pk,
                "special_id": "1",
                "isbn": "12345",
            }
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["special_id"] == [
            "Book with this Special id already exists."
        ]

    async def test_inherited_unique_together(self):
        title = "Boss"
        form = BookForm({"title": title, "author": self.writer.pk})
        assert await sync_to_async(form.is_valid)()
        await form.asave()
        form = DerivedBookForm(
            {"title": title, "author": self.writer.pk, "isbn": "12345"}
        )
        assert await sync_to_async(form.is_valid)() is False
        assert len(form.errors) == 1
        assert form.errors["__all__"] == [
            "Book with this Title and Author already exists."
        ]

    def test_abstract_inherited_unique(self):
        title = "Boss"
        isbn = "12345"
        DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm(
            {
                "title": "Other",
                "author": self.writer.pk,
                "isbn": isbn,
                "suffix1": "1",
                "suffix2": "2",
            }
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["isbn"] == ["Derived book with this Isbn already exists."]

    def test_abstract_inherited_unique_together(self):
        title = "Boss"
        isbn = "12345"
        DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm(
            {
                "title": "Other",
                "author": self.writer.pk,
                "isbn": "9876",
                "suffix1": "0",
                "suffix2": "0",
            }
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["__all__"] == [
            "Derived book with this Suffix1 and Suffix2 already exists."
        ]

    def test_explicitpk_unspecified(self):
        """Test for primary_key being in the form and failing validation."""
        form = ExplicitPKForm({"key": "", "desc": ""})
        assert form.is_valid() is False

    async def test_explicitpk_unique(self):
        """Ensure keys and blank character strings are tested for uniqueness."""
        form = ExplicitPKForm({"key": "key1", "desc": ""})
        assert await sync_to_async(form.is_valid)()
        await form.asave()
        form = ExplicitPKForm({"key": "key1", "desc": ""})
        assert await sync_to_async(form.is_valid)() is False
        if connection.features.interprets_empty_strings_as_nulls:
            assert len(form.errors) == 1
            assert form.errors["key"] == ["Explicit pk with this Key already exists."]
        else:
            assert len(form.errors) == 3
            assert form.errors["__all__"] == [
                "Explicit pk with this Key and Desc already exists."
            ]
            assert form.errors["desc"] == ["Explicit pk with this Desc already exists."]
            assert form.errors["key"] == ["Explicit pk with this Key already exists."]

    def test_unique_for_date(self):
        p = Post.objects.create(
            title="Django 1.0 is released",
            slug="Django 1.0",
            subtitle="Finally",
            posted=datetime.date(2008, 9, 3),
        )
        form = PostForm({"title": "Django 1.0 is released", "posted": "2008-09-03"})
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["title"] == ["Title must be unique for Posted date."]
        form = PostForm({"title": "Work on Django 1.1 begins", "posted": "2008-09-03"})
        assert form.is_valid()
        form = PostForm({"title": "Django 1.0 is released", "posted": "2008-09-04"})
        assert form.is_valid()
        form = PostForm({"slug": "Django 1.0", "posted": "2008-01-01"})
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["slug"] == ["Slug must be unique for Posted year."]
        form = PostForm({"subtitle": "Finally", "posted": "2008-09-30"})
        assert form.is_valid() is False
        assert form.errors["subtitle"] == ["Subtitle must be unique for Posted month."]
        data = {
            "subtitle": "Finally",
            "title": "Django 1.0 is released",
            "slug": "Django 1.0",
            "posted": "2008-09-03",
        }
        form = PostForm(data, instance=p)
        assert form.is_valid()
        form = PostForm({"title": "Django 1.0 is released"})
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["posted"] == ["This field is required."]

    def test_unique_for_date_in_exclude(self):
        """
        If the date for unique_for_* constraints is excluded from the
        ModelForm (in this case 'posted' has editable=False, then the
        constraint should be ignored.
        """

        class DateTimePostForm(AsyncModelForm):
            class Meta:
                model = DateTimePost
                fields = "__all__"

        DateTimePost.objects.create(
            title="Django 1.0 is released",
            slug="Django 1.0",
            subtitle="Finally",
            posted=datetime.datetime(2008, 9, 3, 10, 10, 1),
        )
        # 'title' has unique_for_date='posted'
        form = DateTimePostForm(
            {"title": "Django 1.0 is released", "posted": "2008-09-03"}
        )
        assert form.is_valid()
        # 'slug' has unique_for_year='posted'
        form = DateTimePostForm({"slug": "Django 1.0", "posted": "2008-01-01"})
        assert form.is_valid()
        # 'subtitle' has unique_for_month='posted'
        form = DateTimePostForm({"subtitle": "Finally", "posted": "2008-09-30"})
        assert form.is_valid()

    def test_inherited_unique_for_date(self):
        p = Post.objects.create(
            title="Django 1.0 is released",
            slug="Django 1.0",
            subtitle="Finally",
            posted=datetime.date(2008, 9, 3),
        )
        form = DerivedPostForm(
            {"title": "Django 1.0 is released", "posted": "2008-09-03"}
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["title"] == ["Title must be unique for Posted date."]
        form = DerivedPostForm(
            {"title": "Work on Django 1.1 begins", "posted": "2008-09-03"}
        )
        assert form.is_valid()
        form = DerivedPostForm(
            {"title": "Django 1.0 is released", "posted": "2008-09-04"}
        )
        assert form.is_valid()
        form = DerivedPostForm({"slug": "Django 1.0", "posted": "2008-01-01"})
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert form.errors["slug"] == ["Slug must be unique for Posted year."]
        form = DerivedPostForm({"subtitle": "Finally", "posted": "2008-09-30"})
        assert form.is_valid() is False
        assert form.errors["subtitle"] == ["Subtitle must be unique for Posted month."]
        data = {
            "subtitle": "Finally",
            "title": "Django 1.0 is released",
            "slug": "Django 1.0",
            "posted": "2008-09-03",
        }
        form = DerivedPostForm(data, instance=p)
        assert form.is_valid()

    def test_unique_for_date_with_nullable_date(self):
        class FlexDatePostForm(AsyncModelForm):
            class Meta:
                model = FlexibleDatePost
                fields = "__all__"

        p = FlexibleDatePost.objects.create(
            title="Django 1.0 is released",
            slug="Django 1.0",
            subtitle="Finally",
            posted=datetime.date(2008, 9, 3),
        )

        form = FlexDatePostForm({"title": "Django 1.0 is released"})
        assert form.is_valid()
        form = FlexDatePostForm({"slug": "Django 1.0"})
        assert form.is_valid()
        form = FlexDatePostForm({"subtitle": "Finally"})
        assert form.is_valid()
        data = {
            "subtitle": "Finally",
            "title": "Django 1.0 is released",
            "slug": "Django 1.0",
        }
        form = FlexDatePostForm(data, instance=p)
        assert form.is_valid()

    def test_override_unique_message(self):
        class CustomProductForm(ProductForm):
            class Meta(ProductForm.Meta):
                error_messages = {
                    "slug": {
                        "unique": "%(model_name)s's %(field_label)s not unique.",
                    }
                }

        Product.objects.create(slug="teddy-bear-blue")
        form = CustomProductForm({"slug": "teddy-bear-blue"})
        assert len(form.errors) == 1
        assert form.errors["slug"] == ["Product's Slug not unique."]

    def test_override_unique_together_message(self):
        class CustomPriceForm(PriceForm):
            class Meta(PriceForm.Meta):
                error_messages = {
                    NON_FIELD_ERRORS: {
                        "unique_together": (
                            "%(model_name)s's %(field_labels)s not unique."
                        ),
                    }
                }

        Price.objects.create(price=6.00, quantity=1)
        form = CustomPriceForm({"price": "6.00", "quantity": "1"})
        assert len(form.errors) == 1
        assert form.errors[NON_FIELD_ERRORS] == [
            "Price's Price and Quantity not unique."
        ]

    def test_override_unique_for_date_message(self):
        class CustomPostForm(PostForm):
            class Meta(PostForm.Meta):
                error_messages = {
                    "title": {
                        "unique_for_date": (
                            "%(model_name)s's %(field_label)s not unique "
                            "for %(date_field_label)s date."
                        ),
                    }
                }

        Post.objects.create(
            title="Django 1.0 is released",
            slug="Django 1.0",
            subtitle="Finally",
            posted=datetime.date(2008, 9, 3),
        )
        form = CustomPostForm(
            {"title": "Django 1.0 is released", "posted": "2008-09-03"}
        )
        assert len(form.errors) == 1
        assert form.errors["title"] == ["Post's Title not unique for Posted date."]


@pytest.mark.django_db(transaction=True)
class TestModelFormBasic:
    async def create_basic_data(self):
        self.c1 = await Category.objects.acreate(
            name="Entertainment", slug="entertainment", url="entertainment"
        )
        self.c2 = await Category.objects.acreate(
            name="It's a test", slug="its-test", url="test"
        )
        self.c3 = await Category.objects.acreate(
            name="Third test", slug="third-test", url="third"
        )
        self.w_royko = await Writer.objects.acreate(name="Mike Royko")
        self.w_woodward = await Writer.objects.acreate(name="Bob Woodward")

    def test_base_form(self):
        assert Category.objects.count() == 0
        f = BaseCategoryForm()
        assertHTMLEqual(
            str(f),
            '<div><label for="id_name">Name:</label><input type="text" name="name" '
            'maxlength="20" required id="id_name"></div><div><label for="id_slug">Slug:'
            '</label><input type="text" name="slug" maxlength="20" required '
            'id="id_slug"></div><div><label for="id_url">The URL:</label>'
            '<input type="text" name="url" maxlength="40" required id="id_url"></div>',
        )
        assertHTMLEqual(
            str(f.as_ul()),
            """
            <li><label for="id_name">Name:</label>
            <input id="id_name" type="text" name="name" maxlength="20" required></li>
            <li><label for="id_slug">Slug:</label>
            <input id="id_slug" type="text" name="slug" maxlength="20" required></li>
            <li><label for="id_url">The URL:</label>
            <input id="id_url" type="text" name="url" maxlength="40" required></li>
            """,
        )
        assertHTMLEqual(
            str(f["name"]),
            """<input id="id_name" type="text" name="name" maxlength="20" required>""",
        )

    def test_auto_id(self):
        f = BaseCategoryForm(auto_id=False)
        assertHTMLEqual(
            str(f.as_ul()),
            """<li>Name: <input type="text" name="name" maxlength="20" required></li>
<li>Slug: <input type="text" name="slug" maxlength="20" required></li>
<li>The URL: <input type="text" name="url" maxlength="40" required></li>""",
        )

    async def test_initial_values(self):
        await self.create_basic_data()
        # Initial values can be provided for model forms
        f = ArticleForm(
            auto_id=False,
            initial={
                "headline": "Your headline here",
                "categories": [str(self.c1.id), str(self.c2.id)],
            },
        )
        assertHTMLEqual(
            await sync_to_async(f.as_ul)(),
            """
            <li>Headline:
            <input type="text" name="headline" value="Your headline here" maxlength="50"
                required>
            </li>
            <li>Slug: <input type="text" name="slug" maxlength="50" required></li>
            <li>Pub date: <input type="text" name="pub_date" required></li>
            <li>Writer: <select name="writer" required>
            <option value="" selected>---------</option>
            <option value="%s">Bob Woodward</option>
            <option value="%s">Mike Royko</option>
            </select></li>
            <li>Article:
            <textarea rows="10" cols="40" name="article" required></textarea></li>
            <li>Categories: <select multiple name="categories">
            <option value="%s" selected>Entertainment</option>
            <option value="%s" selected>It&#x27;s a test</option>
            <option value="%s">Third test</option>
            </select></li>
            <li>Status: <select name="status">
            <option value="" selected>---------</option>
            <option value="1">Draft</option>
            <option value="2">Pending</option>
            <option value="3">Live</option>
            </select></li>
            """
            % (self.w_woodward.pk, self.w_royko.pk, self.c1.pk, self.c2.pk, self.c3.pk),
        )

        # When the ModelForm is passed an instance, that instance's current values are
        # inserted as 'initial' data in each Field.
        f = RoykoForm(auto_id=False, instance=self.w_royko)
        assertHTMLEqual(
            str(f),
            '<div>Name:<div class="helptext">Use both first and last names.</div>'
            '<input type="text" name="name" value="Mike Royko" maxlength="50" '
            "required></div>",
        )

        art = await Article.objects.acreate(
            headline="Test article",
            slug="test-article",
            pub_date=datetime.date(1988, 1, 4),
            writer=self.w_royko,
            article="Hello.",
        )
        art_id_1 = art.id

        f = await sync_to_async(ArticleForm)(auto_id=False, instance=art)
        assertHTMLEqual(
            await sync_to_async(f.as_ul)(),
            """
            <li>Headline:
            <input type="text" name="headline" value="Test article" maxlength="50"
                required>
            </li>
            <li>Slug:
            <input type="text" name="slug" value="test-article" maxlength="50" required>
            </li>
            <li>Pub date:
            <input type="text" name="pub_date" value="1988-01-04" required></li>
            <li>Writer: <select name="writer" required>
            <option value="">---------</option>
            <option value="%s">Bob Woodward</option>
            <option value="%s" selected>Mike Royko</option>
            </select></li>
            <li>Article:
            <textarea rows="10" cols="40" name="article" required>Hello.</textarea></li>
            <li>Categories: <select multiple name="categories">
            <option value="%s">Entertainment</option>
            <option value="%s">It&#x27;s a test</option>
            <option value="%s">Third test</option>
            </select></li>
            <li>Status: <select name="status">
            <option value="" selected>---------</option>
            <option value="1">Draft</option>
            <option value="2">Pending</option>
            <option value="3">Live</option>
            </select></li>
            """
            % (self.w_woodward.pk, self.w_royko.pk, self.c1.pk, self.c2.pk, self.c3.pk),
        )

        f = await sync_to_async(ArticleForm)(
            {
                "headline": "Test headline",
                "slug": "test-headline",
                "pub_date": "1984-02-06",
                "writer": str(self.w_royko.pk),
                "article": "Hello.",
            },
            instance=art,
        )
        await sync_to_async(f.full_clean)()
        assert f.errors == {}
        assert f.is_valid()
        test_art = await f.asave()
        assert test_art.id == art_id_1
        test_art = await Article.objects.aget(id=art_id_1)
        assert test_art.headline == "Test headline"

    async def test_m2m_initial_callable(self):
        """
        A callable can be provided as the initial value for an m2m field.
        """
        self.maxDiff = 1200
        await self.create_basic_data()

        # Set up a callable initial value
        def formfield_for_dbfield(db_field, **kwargs):
            if db_field.name == "categories":
                kwargs["initial"] = lambda: Category.objects.order_by("name")[:2]
            return db_field.formfield(**kwargs)

        # Create a ModelForm, instantiate it, and check that the output is as expected
        ModelForm = await sync_to_async(modelform_factory)(
            Article,
            fields=["headline", "categories"],
            formfield_callback=formfield_for_dbfield,
            form=AsyncModelForm,
        )
        form = ModelForm()
        assertHTMLEqual(
            await sync_to_async(form.as_ul)(),
            """<li><label for="id_headline">Headline:</label>
<input id="id_headline" type="text" name="headline" maxlength="50" required></li>
<li><label for="id_categories">Categories:</label>
<select multiple name="categories" id="id_categories">
<option value="%d" selected>Entertainment</option>
<option value="%d" selected>It&#x27;s a test</option>
<option value="%d">Third test</option>
</select></li>"""
            % (self.c1.pk, self.c2.pk, self.c3.pk),
        )

    async def test_basic_creation(self):
        assert await Category.objects.acount() == 0
        f = BaseCategoryForm(
            {
                "name": "Entertainment",
                "slug": "entertainment",
                "url": "entertainment",
            }
        )
        assert f.is_valid()
        assert f.cleaned_data["name"] == "Entertainment"
        assert f.cleaned_data["slug"] == "entertainment"
        assert f.cleaned_data["url"] == "entertainment"
        c1 = await f.asave()
        # Testing whether the same object is returned from the
        # ORM... not the fastest way...

        assert await Category.objects.acount() == 1
        assert c1 == await Category.objects.afirst()
        assert c1.name == "Entertainment"

    async def test_save_commit_false(self):
        # If you call save() with commit=False, then it will return an object that
        # hasn't yet been saved to the database. In this case, it's up to you to call
        # save() on the resulting model instance.
        f = BaseCategoryForm(
            {"name": "Third test", "slug": "third-test", "url": "third"}
        )
        assert f.is_valid()
        c1 = await f.asave(commit=False)
        assert c1.name == "Third test"
        assert await Category.objects.acount() == 0
        await c1.asave()
        assert await Category.objects.acount() == 1

    async def test_save_with_data_errors(self):
        # If you call save() with invalid data, you'll get a ValueError.
        f = BaseCategoryForm({"name": "", "slug": "not a slug!", "url": "foo"})
        assert f.errors["name"] == ["This field is required."]
        assert f.errors["slug"] == [
            "Enter a valid “slug” consisting of letters, numbers, underscores or "
            "hyphens."
        ]
        assert f.cleaned_data == {"url": "foo"}
        msg = "The Category could not be created because the data didn't validate."
        with pytest.raises(ValueError, match=msg):
            await f.asave()
        f = BaseCategoryForm({"name": "", "slug": "", "url": "foo"})
        with pytest.raises(ValueError, match=msg):
            await f.asave()

    async def test_multi_fields(self):
        await self.create_basic_data()
        self.maxDiff = None
        # ManyToManyFields are represented by a MultipleChoiceField, ForeignKeys and any
        # fields with the 'choices' attribute are represented by a ChoiceField.
        f = ArticleForm(auto_id=False)
        assertHTMLEqual(
            await sync_to_async(str)(f),
            """
            <div>Headline:
                <input type="text" name="headline" maxlength="50" required>
            </div>
            <div>Slug:
                <input type="text" name="slug" maxlength="50" required>
            </div>
            <div>Pub date:
                <input type="text" name="pub_date" required>
            </div>
            <div>Writer:
                <select name="writer" required>
                    <option value="" selected>---------</option>
                    <option value="%s">Bob Woodward</option>
                    <option value="%s">Mike Royko</option>
                </select>
            </div>
            <div>Article:
                <textarea name="article" cols="40" rows="10" required></textarea>
            </div>
            <div>Categories:
                <select name="categories" multiple>
                    <option value="%s">Entertainment</option>
                    <option value="%s">It&#x27;s a test</option>
                    <option value="%s">Third test</option>
                </select>
            </div>
            <div>Status:
                <select name="status">
                    <option value="" selected>---------</option>
                    <option value="1">Draft</option><option value="2">Pending</option>
                    <option value="3">Live</option>
                </select>
            </div>
            """
            % (self.w_woodward.pk, self.w_royko.pk, self.c1.pk, self.c2.pk, self.c3.pk),
        )

        # Add some categories and test the many-to-many form output.
        new_art = await Article.objects.acreate(
            article="Hello.",
            headline="New headline",
            slug="new-headline",
            pub_date=datetime.date(1988, 1, 4),
            writer=self.w_royko,
        )
        await new_art.categories.aadd(await Category.objects.aget(name="Entertainment"))
        assert [art async for art in new_art.categories.all()] == [self.c1]
        f = await sync_to_async(ArticleForm)(auto_id=False, instance=new_art)
        assertHTMLEqual(
            await sync_to_async(f.as_ul)(),
            """
            <li>Headline:
            <input type="text" name="headline" value="New headline" maxlength="50"
                required>
            </li>
            <li>Slug:
            <input type="text" name="slug" value="new-headline" maxlength="50" required>
            </li>
            <li>Pub date:
            <input type="text" name="pub_date" value="1988-01-04" required></li>
            <li>Writer: <select name="writer" required>
            <option value="">---------</option>
            <option value="%s">Bob Woodward</option>
            <option value="%s" selected>Mike Royko</option>
            </select></li>
            <li>Article:
            <textarea rows="10" cols="40" name="article" required>Hello.</textarea></li>
            <li>Categories: <select multiple name="categories">
            <option value="%s" selected>Entertainment</option>
            <option value="%s">It&#x27;s a test</option>
            <option value="%s">Third test</option>
            </select></li>
            <li>Status: <select name="status">
            <option value="" selected>---------</option>
            <option value="1">Draft</option>
            <option value="2">Pending</option>
            <option value="3">Live</option>
            </select></li>
            """
            % (self.w_woodward.pk, self.w_royko.pk, self.c1.pk, self.c2.pk, self.c3.pk),
        )

    async def test_subset_fields(self):
        # You can restrict a form to a subset of the complete list of fields
        # by providing a 'fields' argument. If you try to save a
        # model created with such a form, you need to ensure that the fields
        # that are _not_ on the form have default values, or are allowed to have
        # a value of None. If a field isn't specified on a form, the object created
        # from the form can't provide a value for that field!
        class PartialArticleForm(AsyncModelForm):
            class Meta:
                model = Article
                fields = ("headline", "pub_date")

        f = PartialArticleForm(auto_id=False)
        assertHTMLEqual(
            str(f),
            '<div>Headline:<input type="text" name="headline" maxlength="50" required>'
            '</div><div>Pub date:<input type="text" name="pub_date" required></div>',
        )

        class PartialArticleFormWithSlug(AsyncModelForm):
            class Meta:
                model = Article
                fields = ("headline", "slug", "pub_date")

        w_royko = await Writer.objects.acreate(name="Mike Royko")
        art = await Article.objects.acreate(
            article="Hello.",
            headline="New headline",
            slug="new-headline",
            pub_date=datetime.date(1988, 1, 4),
            writer=w_royko,
        )
        f = PartialArticleFormWithSlug(
            {
                "headline": "New headline",
                "slug": "new-headline",
                "pub_date": "1988-01-04",
            },
            auto_id=False,
            instance=art,
        )
        assertHTMLEqual(
            f.as_ul(),
            """
            <li>Headline:
            <input type="text" name="headline" value="New headline" maxlength="50"
                required>
            </li>
            <li>Slug:
            <input type="text" name="slug" value="new-headline" maxlength="50"
                required>
            </li>
            <li>Pub date:
            <input type="text" name="pub_date" value="1988-01-04" required></li>
            """,
        )
        assert f.is_valid()
        new_art = await f.asave()
        assert new_art.id == art.id
        new_art = await Article.objects.aget(id=art.id)
        assert new_art.headline == "New headline"

    async def test_m2m_editing(self):
        await self.create_basic_data()
        form_data = {
            "headline": "New headline",
            "slug": "new-headline",
            "pub_date": "1988-01-04",
            "writer": str(self.w_royko.pk),
            "article": "Hello.",
            "categories": [str(self.c1.id), str(self.c2.id)],
        }
        # Create a new article, with categories, via the form.
        f = ArticleForm(form_data)
        new_art = await f.asave()
        new_art = await Article.objects.aget(id=new_art.id)
        art_id_1 = new_art.id
        assert [art async for art in new_art.categories.order_by("name")] == [
            self.c1,
            self.c2,
        ]

        # Now, submit form data with no categories. This deletes the existing
        # categories.
        form_data["categories"] = []
        f = await sync_to_async(ArticleForm)(form_data, instance=new_art)
        new_art = await f.asave()
        assert new_art.id == art_id_1
        new_art = await Article.objects.aget(id=art_id_1)
        assert [art async for art in new_art.categories.all()] == []

        # Create a new article, with no categories, via the form.
        f = ArticleForm(form_data)
        new_art = await f.asave()
        art_id_2 = new_art.id
        assert art_id_2 not in (None, art_id_1)
        new_art = await Article.objects.aget(id=art_id_2)
        assert [art async for art in new_art.categories.all()] == []

        # Create a new article, with categories, via the form, but use commit=False.
        # The m2m data won't be saved until save_m2m() is invoked on the form.
        form_data["categories"] = [str(self.c1.id), str(self.c2.id)]
        f = ArticleForm(form_data)
        new_art = await f.asave(commit=False)

        # Manually save the instance
        await new_art.asave()
        art_id_3 = new_art.id
        assert art_id_3 not in (None, art_id_1, art_id_2)

        # The instance doesn't have m2m data yet
        new_art = await Article.objects.aget(id=art_id_3)
        assert [art async for art in new_art.categories.all()] == []

        # Save the m2m data on the form
        await f.asave_m2m()
        assert [art async for art in new_art.categories.order_by("name")] == [
            self.c1,
            self.c2,
        ]

    async def test_custom_form_fields(self):
        # Here, we define a custom ModelForm. Because it happens to have the
        # same fields as the Category model, we can just call the form's save()
        # to apply its changes to an existing Category instance.
        class ShortCategory(AsyncModelForm):
            name = forms.CharField(max_length=5)
            slug = forms.CharField(max_length=5)
            url = forms.CharField(max_length=3)

            class Meta:
                model = Category
                fields = "__all__"

        cat = await Category.objects.acreate(name="Third test")
        form = ShortCategory(
            {"name": "Third", "slug": "third", "url": "3rd"}, instance=cat
        )
        data = await form.asave()
        assert data.name == "Third"
        category = await Category.objects.aget(id=cat.id)
        assert category.name == "Third"

    async def test_runtime_choicefield_populated(self):
        self.maxDiff = None
        # Here, we demonstrate that choices for a ForeignKey ChoiceField are determined
        # at runtime, based on the data in the database when the form is displayed, not
        # the data in the database when the form is instantiated.
        await self.create_basic_data()
        f = ArticleForm(auto_id=False)
        assertHTMLEqual(
            await sync_to_async(f.as_ul)(),
            '<li>Headline: <input type="text" name="headline" maxlength="50" required>'
            "</li>"
            '<li>Slug: <input type="text" name="slug" maxlength="50" required></li>'
            '<li>Pub date: <input type="text" name="pub_date" required></li>'
            '<li>Writer: <select name="writer" required>'
            '<option value="" selected>---------</option>'
            '<option value="%s">Bob Woodward</option>'
            '<option value="%s">Mike Royko</option>'
            "</select></li>"
            '<li>Article: <textarea rows="10" cols="40" name="article" required>'
            "</textarea></li>"
            '<li>Categories: <select multiple name="categories">'
            '<option value="%s">Entertainment</option>'
            '<option value="%s">It&#x27;s a test</option>'
            '<option value="%s">Third test</option>'
            "</select> </li>"
            '<li>Status: <select name="status">'
            '<option value="" selected>---------</option>'
            '<option value="1">Draft</option>'
            '<option value="2">Pending</option>'
            '<option value="3">Live</option>'
            "</select></li>"
            % (self.w_woodward.pk, self.w_royko.pk, self.c1.pk, self.c2.pk, self.c3.pk),
        )

        c4 = await Category.objects.acreate(name="Fourth", url="4th")
        w_bernstein = await Writer.objects.acreate(name="Carl Bernstein")
        assertHTMLEqual(
            await sync_to_async(f.as_ul)(),
            '<li>Headline: <input type="text" name="headline" maxlength="50" required>'
            "</li>"
            '<li>Slug: <input type="text" name="slug" maxlength="50" required></li>'
            '<li>Pub date: <input type="text" name="pub_date" required></li>'
            '<li>Writer: <select name="writer" required>'
            '<option value="" selected>---------</option>'
            '<option value="%s">Bob Woodward</option>'
            '<option value="%s">Carl Bernstein</option>'
            '<option value="%s">Mike Royko</option>'
            "</select></li>"
            '<li>Article: <textarea rows="10" cols="40" name="article" required>'
            "</textarea></li>"
            '<li>Categories: <select multiple name="categories">'
            '<option value="%s">Entertainment</option>'
            '<option value="%s">It&#x27;s a test</option>'
            '<option value="%s">Third test</option>'
            '<option value="%s">Fourth</option>'
            "</select></li>"
            '<li>Status: <select name="status">'
            '<option value="" selected>---------</option>'
            '<option value="1">Draft</option>'
            '<option value="2">Pending</option>'
            '<option value="3">Live</option>'
            "</select></li>"
            % (
                self.w_woodward.pk,
                w_bernstein.pk,
                self.w_royko.pk,
                self.c1.pk,
                self.c2.pk,
                self.c3.pk,
                c4.pk,
            ),
        )

    @isolate_apps("test_model_forms")
    def test_callable_choices_are_lazy(self):
        call_count = 0

        def get_animal_choices():
            nonlocal call_count
            call_count += 1
            return [("LION", "Lion"), ("ZEBRA", "Zebra")]

        class ZooKeeper(models.Model):
            animal = models.CharField(
                blank=True,
                choices=get_animal_choices,
                max_length=5,
            )

        class ZooKeeperForm(AsyncModelForm):
            class Meta:
                model = ZooKeeper
                fields = ["animal"]

        assert call_count == 0
        form = ZooKeeperForm()
        assert call_count == 0
        assert isinstance(form.fields["animal"].choices, BlankChoiceIterator)
        assert call_count == 0
        assert form.fields["animal"].choices == models.BLANK_CHOICE_DASH + [
            ("LION", "Lion"),
            ("ZEBRA", "Zebra"),
        ]
        assert call_count == 1

    async def test_recleaning_model_form_instance(self):
        """
        Re-cleaning an instance that was added via a ModelForm shouldn't raise
        a pk uniqueness error.
        """

        class AuthorForm(AsyncModelForm):
            class Meta:
                model = Author
                fields = "__all__"

        form = AuthorForm({"full_name": "Bob"})
        assert form.is_valid()
        obj = await form.asave()
        obj.name = "Alice"
        obj.full_clean()

    def test_validate_foreign_key_uses_default_manager(self):
        class MyForm(AsyncModelForm):
            class Meta:
                model = Article
                fields = "__all__"

        # Archived writers are filtered out by the default manager.
        w = Writer.objects.create(name="Randy", archived=True)
        data = {
            "headline": "My Article",
            "slug": "my-article",
            "pub_date": datetime.date.today(),
            "writer": w.pk,
            "article": "lorem ipsum",
        }
        form = MyForm(data)
        assert form.is_valid() is False
        assert form.errors == {
            "writer": [
                "Select a valid choice. That choice is not one of the available "
                "choices."
            ]
        }

    async def test_validate_foreign_key_to_model_with_overridden_manager(self):
        class MyForm(AsyncModelForm):
            class Meta:
                model = Article
                fields = "__all__"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Allow archived authors.
                self.fields["writer"].queryset = Writer._base_manager.all()

        w = await Writer.objects.acreate(name="Randy", archived=True)
        data = {
            "headline": "My Article",
            "slug": "my-article",
            "pub_date": datetime.date.today(),
            "writer": w.pk,
            "article": "lorem ipsum",
        }
        form = MyForm(data)
        assert await sync_to_async(form.is_valid)()
        article = await form.asave()
        assert article.writer == w


@pytest.mark.django_db
class TestModelMultipleChoiceField:
    @pytest.fixture(autouse=True)
    def setup(cls):
        cls.c1 = Category.objects.create(
            name="Entertainment", slug="entertainment", url="entertainment"
        )
        cls.c2 = Category.objects.create(
            name="It's a test", slug="its-test", url="test"
        )
        cls.c3 = Category.objects.create(name="Third", slug="third-test", url="third")

    def test_model_multiple_choice_field(self):
        f = forms.ModelMultipleChoiceField(Category.objects.all())
        assert list(f.choices) == [
            (self.c1.pk, "Entertainment"),
            (self.c2.pk, "It's a test"),
            (self.c3.pk, "Third"),
        ]
        with pytest.raises(ValidationError):
            f.clean(None)
        with pytest.raises(ValidationError):
            f.clean([])
        assert list(f.clean([self.c1.id])) == [self.c1]
        assert list(f.clean([self.c2.id])) == [self.c2]
        assert list(f.clean([str(self.c1.id)])) == [self.c1]
        assert list(f.clean([str(self.c1.id), str(self.c2.id)])) == [self.c1, self.c2]
        assert list(f.clean([self.c1.id, str(self.c2.id)])) == [self.c1, self.c2]
        assert list(f.clean((self.c1.id, str(self.c2.id)))) == [self.c1, self.c2]
        with pytest.raises(ValidationError):
            f.clean(["0"])
        with pytest.raises(ValidationError):
            f.clean("hello")
        with pytest.raises(ValidationError):
            f.clean(["fail"])

        # Invalid types that require TypeError to be caught (#22808).
        with pytest.raises(ValidationError):
            f.clean([["fail"]])
        with pytest.raises(ValidationError):
            f.clean([{"foo": "bar"}])

        # Add a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        # Note, we are using an id of 1006 here since tests that run before
        # this may create categories with primary keys up to 6. Use
        # a number that will not conflict.
        c6 = Category.objects.create(id=1006, name="Sixth", url="6th")
        assert list(f.clean([c6.id])) == [c6]

        # Delete a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        Category.objects.get(url="6th").delete()
        with pytest.raises(ValidationError):
            f.clean([c6.id])

    def test_model_multiple_choice_required_false(self):
        f = forms.ModelMultipleChoiceField(Category.objects.all(), required=False)
        assert isinstance(f.clean([]), EmptyQuerySet)
        with pytest.raises(ValidationError):
            f.clean(["0"])
        with pytest.raises(ValidationError):
            f.clean([str(self.c3.id), "0"])
        with pytest.raises(ValidationError):
            f.clean([str(self.c1.id), "0"])

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name="Third")
        assert list(f.choices) == [
            (self.c1.pk, "Entertainment"),
            (self.c2.pk, "It's a test"),
        ]
        assert list(f.clean([self.c2.id])) == [self.c2]
        with pytest.raises(ValidationError):
            f.clean([self.c3.id])
        with pytest.raises(ValidationError):
            f.clean([str(self.c2.id), str(self.c3.id)])

        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "multicategory " + str(obj)
        assert list(f.choices) == [
            (self.c1.pk, "multicategory Entertainment"),
            (self.c2.pk, "multicategory It's a test"),
            (self.c3.pk, "multicategory Third"),
        ]

    def test_model_multiple_choice_number_of_queries(self):
        """
        ModelMultipleChoiceField does O(1) queries instead of O(n) (#10156).
        """
        persons = [Writer.objects.create(name="Person %s" % i) for i in range(30)]

        f = forms.ModelMultipleChoiceField(queryset=Writer.objects.all())
        assertNumQueries(1, f.clean, [p.pk for p in persons[1:11:2]])

    def test_model_multiple_choice_null_characters(self):
        f = forms.ModelMultipleChoiceField(queryset=ExplicitPK.objects.all())
        msg = "Null characters are not allowed."
        with pytest.raises(ValidationError, match=msg):
            f.clean(["\x00something"])

        with pytest.raises(ValidationError, match=msg):
            f.clean(["valid", "\x00something"])

    def test_model_multiple_choice_run_validators(self):
        """
        ModelMultipleChoiceField run given validators (#14144).
        """
        for i in range(30):
            Writer.objects.create(name="Person %s" % i)

        self._validator_run = False

        def my_validator(value):
            self._validator_run = True

        f = forms.ModelMultipleChoiceField(
            queryset=Writer.objects.all(), validators=[my_validator]
        )
        f.clean([p.pk for p in Writer.objects.all()[8:9]])
        assert self._validator_run

    def test_model_multiple_choice_show_hidden_initial(self):
        """
        Test support of show_hidden_initial by ModelMultipleChoiceField.
        """

        class WriterForm(forms.Form):
            persons = forms.ModelMultipleChoiceField(
                show_hidden_initial=True, queryset=Writer.objects.all()
            )

        person1 = Writer.objects.create(name="Person 1")
        person2 = Writer.objects.create(name="Person 2")

        form = WriterForm(
            initial={"persons": [person1, person2]},
            data={
                "initial-persons": [str(person1.pk), str(person2.pk)],
                "persons": [str(person1.pk), str(person2.pk)],
            },
        )
        assert form.is_valid()
        assert form.has_changed() is False

        form = WriterForm(
            initial={"persons": [person1, person2]},
            data={
                "initial-persons": [str(person1.pk), str(person2.pk)],
                "persons": [str(person2.pk)],
            },
        )
        assert form.is_valid()
        assert form.has_changed()

    def test_model_multiple_choice_field_22745(self):
        """
        #22745 -- Make sure that ModelMultipleChoiceField with
        CheckboxSelectMultiple widget doesn't produce unnecessary db queries
        when accessing its BoundField's attrs.
        """

        class ModelMultipleChoiceForm(forms.Form):
            categories = forms.ModelMultipleChoiceField(
                Category.objects.all(), widget=forms.CheckboxSelectMultiple
            )

        form = ModelMultipleChoiceForm()
        field = form["categories"]  # BoundField
        template = Template("{{ field.name }}{{ field }}{{ field.help_text }}")
        with assertNumQueries(1):
            template.render(Context({"field": field}))

    def test_show_hidden_initial_changed_queries_efficiently(self):
        class WriterForm(forms.Form):
            persons = forms.ModelMultipleChoiceField(
                show_hidden_initial=True, queryset=Writer.objects.all()
            )

        writers = (Writer.objects.create(name=str(x)) for x in range(0, 50))
        writer_pks = tuple(x.pk for x in writers)
        form = WriterForm(data={"initial-persons": writer_pks})
        with assertNumQueries(1):
            assert form.has_changed()

    def test_clean_does_deduplicate_values(self):
        class PersonForm(forms.Form):
            persons = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

        person1 = Person.objects.create(name="Person 1")
        form = PersonForm(data={})
        queryset = form.fields["persons"].clean([str(person1.pk)] * 50)
        sql, params = queryset.query.sql_with_params()
        assert len(params) == 1

    def test_to_field_name_with_initial_data(self):
        class ArticleCategoriesForm(AsyncModelForm):
            categories = forms.ModelMultipleChoiceField(
                Category.objects.all(), to_field_name="slug"
            )

            class Meta:
                model = Article
                fields = ["categories"]

        article = Article.objects.create(
            headline="Test article",
            slug="test-article",
            pub_date=datetime.date(1988, 1, 4),
            writer=Writer.objects.create(name="Test writer"),
            article="Hello.",
        )
        article.categories.add(self.c2, self.c3)
        form = ArticleCategoriesForm(instance=article)
        assert form["categories"].value() == [self.c2.slug, self.c3.slug]


@pytest.mark.django_db(transaction=True)
class TestModelOneToOneField:
    def test_modelform_onetoonefield(self):
        class ImprovedArticleForm(AsyncModelForm):
            class Meta:
                model = ImprovedArticle
                fields = "__all__"

        class ImprovedArticleWithParentLinkForm(AsyncModelForm):
            class Meta:
                model = ImprovedArticleWithParentLink
                fields = "__all__"

        assert list(ImprovedArticleForm.base_fields) == ["article"]
        assert list(ImprovedArticleWithParentLinkForm.base_fields) == []

    async def test_modelform_subclassed_model(self):
        class BetterWriterForm(AsyncModelForm):
            class Meta:
                # BetterWriter model is a subclass of Writer with an additional
                # `score` field.
                model = BetterWriter
                fields = "__all__"

        bw = await BetterWriter.objects.acreate(name="Joe Better", score=10)
        assert sorted(model_to_dict(bw)) == ["id", "name", "score", "writer_ptr"]
        assert sorted(model_to_dict(bw, fields=[])) == []
        assert sorted(model_to_dict(bw, fields=["id", "name"])) == ["id", "name"]
        assert sorted(model_to_dict(bw, exclude=[])) == [
            "id",
            "name",
            "score",
            "writer_ptr",
        ]
        assert sorted(model_to_dict(bw, exclude=["id", "name"])) == [
            "score",
            "writer_ptr",
        ]

        form = BetterWriterForm({"name": "Some Name", "score": 12})
        assert form.is_valid()
        bw2 = await form.asave()
        assert bw2.score == 12

    async def test_onetoonefield(self):
        class WriterProfileForm(AsyncModelForm):
            class Meta:
                # WriterProfile has a OneToOneField to Writer
                model = WriterProfile
                fields = "__all__"

        self.w_royko = await Writer.objects.acreate(name="Mike Royko")
        self.w_woodward = await Writer.objects.acreate(name="Bob Woodward")

        form = WriterProfileForm()
        assertHTMLEqual(
            await sync_to_async(form.as_p)(),
            """
            <p><label for="id_writer">Writer:</label>
            <select name="writer" id="id_writer" required>
            <option value="" selected>---------</option>
            <option value="%s">Bob Woodward</option>
            <option value="%s">Mike Royko</option>
            </select></p>
            <p><label for="id_age">Age:</label>
            <input type="number" name="age" id="id_age" min="0" required></p>
            """
            % (
                self.w_woodward.pk,
                self.w_royko.pk,
            ),
        )

        data = {
            "writer": str(self.w_woodward.pk),
            "age": "65",
        }
        form = WriterProfileForm(data)
        instance = await form.asave()
        assert str(instance) == "Bob Woodward is 65"

        form = WriterProfileForm(instance=instance)
        assertHTMLEqual(
            await sync_to_async(form.as_p)(),
            """
            <p><label for="id_writer">Writer:</label>
            <select name="writer" id="id_writer" required>
            <option value="">---------</option>
            <option value="%s" selected>Bob Woodward</option>
            <option value="%s">Mike Royko</option>
            </select></p>
            <p><label for="id_age">Age:</label>
            <input type="number" name="age" value="65" id="id_age" min="0" required>
            </p>"""
            % (
                self.w_woodward.pk,
                self.w_royko.pk,
            ),
        )

    async def test_assignment_of_none(self):
        class AuthorForm(AsyncModelForm):
            class Meta:
                model = Author
                fields = ["publication", "full_name"]

        publication = await Publication.objects.acreate(
            title="Pravda", date_published=datetime.date(1991, 8, 22)
        )
        author = await Author.objects.acreate(
            publication=publication, full_name="John Doe"
        )
        form = AuthorForm({"publication": "", "full_name": "John Doe"}, instance=author)
        assert form.is_valid()
        assert form.cleaned_data["publication"] is None
        author = await form.asave()
        # author object returned from form still retains original publication object
        # that's why we need to retrieve it from database again
        new_author = await Author.objects.aget(pk=author.pk)
        assert new_author.publication is None

    def test_assignment_of_none_null_false(self):
        class AuthorForm(AsyncModelForm):
            class Meta:
                model = Author1
                fields = ["publication", "full_name"]

        publication = Publication.objects.create(
            title="Pravda", date_published=datetime.date(1991, 8, 22)
        )
        author = Author1.objects.create(publication=publication, full_name="John Doe")
        form = AuthorForm({"publication": "", "full_name": "John Doe"}, instance=author)
        assert form.is_valid() is False


@pytest.mark.django_db
class TestFileAndImageField:
    def setUp(self):
        if os.path.exists(temp_storage_dir):
            shutil.rmtree(temp_storage_dir)
        os.mkdir(temp_storage_dir)
        yield
        shutil.rmtree(temp_storage_dir)

    def test_clean_false(self):
        """
        If the ``clean`` method on a non-required FileField receives False as
        the data (meaning clear the field value), it returns False, regardless
        of the value of ``initial``.
        """
        f = forms.FileField(required=False)
        assert f.clean(False) is False
        assert f.clean(False, "initial") is False

    def test_clean_false_required(self):
        """
        If the ``clean`` method on a required FileField receives False as the
        data, it has the same effect as None: initial is returned if non-empty,
        otherwise the validation catches the lack of a required value.
        """
        f = forms.FileField(required=True)
        assert f.clean(False, "initial") == "initial"
        with pytest.raises(ValidationError):
            f.clean(False)

    async def test_full_clear(self):
        """
        Integration happy-path test that a model FileField can actually be set
        and cleared via a ModelForm.
        """

        class DocumentForm(AsyncModelForm):
            class Meta:
                model = Document
                fields = "__all__"

        form = DocumentForm()
        assert 'name="myfile"' in str(form)
        assert "myfile-clear" not in str(form)
        form = DocumentForm(
            files={"myfile": SimpleUploadedFile("something.txt", b"content")}
        )
        assert form.is_valid()
        doc = await form.asave(commit=False)
        assert doc.myfile.name == "something.txt"
        form = DocumentForm(instance=doc)
        assert "myfile-clear" in str(form)
        form = DocumentForm(instance=doc, data={"myfile-clear": "true"})
        doc = await form.asave(commit=False)
        assert bool(doc.myfile) is False

    async def test_clear_and_file_contradiction(self):
        """
        If the user submits a new file upload AND checks the clear checkbox,
        they get a validation error, and the bound redisplay of the form still
        includes the current file and the clear checkbox.
        """

        class DocumentForm(AsyncModelForm):
            class Meta:
                model = Document
                fields = "__all__"

        form = DocumentForm(
            files={"myfile": SimpleUploadedFile("something.txt", b"content")}
        )
        assert form.is_valid()
        doc = await form.asave(commit=False)
        form = DocumentForm(
            instance=doc,
            files={"myfile": SimpleUploadedFile("something.txt", b"content")},
            data={"myfile-clear": "true"},
        )
        assert not form.is_valid()
        assert form.errors["myfile"] == [
            "Please either submit a file or check the clear checkbox, not both."
        ]
        rendered = str(form)
        assert "something.txt" in rendered
        assert "myfile-clear" in rendered

    def test_render_empty_file_field(self):
        class DocumentForm(AsyncModelForm):
            class Meta:
                model = Document
                fields = "__all__"

        doc = Document.objects.create()
        form = DocumentForm(instance=doc)
        assertHTMLEqual(
            str(form["myfile"]), '<input id="id_myfile" name="myfile" type="file">'
        )

    async def test_file_field_data(self):
        # Test conditions when files is either not given or empty.
        f = TextFileForm(data={"description": "Assistance"})
        assert f.is_valid() is False
        f = TextFileForm(data={"description": "Assistance"}, files={})
        assert f.is_valid() is False

        # Upload a file and ensure it all works as expected.
        f = TextFileForm(
            data={"description": "Assistance"},
            files={"file": SimpleUploadedFile("test1.txt", b"hello world")},
        )
        assert f.is_valid()
        assert type(f.cleaned_data["file"]) is SimpleUploadedFile
        instance = await f.asave()
        assert instance.file.name == "tests/test1.txt"
        await sync_to_async(instance.file.delete)()

        # If the previous file has been deleted, the file name can be reused
        f = TextFileForm(
            data={"description": "Assistance"},
            files={"file": SimpleUploadedFile("test1.txt", b"hello world")},
        )
        assert f.is_valid()
        assert type(f.cleaned_data["file"]) is SimpleUploadedFile
        instance = await f.asave()
        assert instance.file.name == "tests/test1.txt"

        # Check if the max_length attribute has been inherited from the model.
        f = TextFileForm(
            data={"description": "Assistance"},
            files={"file": SimpleUploadedFile("test-maxlength.txt", b"hello world")},
        )
        assert f.is_valid() is False

        # Edit an instance that already has the file defined in the model. This will not
        # save the file again, but leave it exactly as it is.
        f = TextFileForm({"description": "Assistance"}, instance=instance)
        assert f.is_valid()
        assert f.cleaned_data["file"].name == "tests/test1.txt"
        instance = await f.asave()
        assert instance.file.name == "tests/test1.txt"

        # Delete the current file since this is not done by Django.
        await sync_to_async(instance.file.delete)()

        # Override the file by uploading a new one.
        f = TextFileForm(
            data={"description": "Assistance"},
            files={"file": SimpleUploadedFile("test2.txt", b"hello world")},
            instance=instance,
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.file.name == "tests/test2.txt"

        # Delete the current file since this is not done by Django.
        await sync_to_async(instance.file.delete)()
        await instance.adelete()

    async def test_filefield_required_false(self):
        # Test the non-required FileField
        f = TextFileForm(data={"description": "Assistance"})
        f.fields["file"].required = False
        assert f.is_valid()
        instance = await f.asave()
        assert instance.file.name == ""

        f = TextFileForm(
            data={"description": "Assistance"},
            files={"file": SimpleUploadedFile("test3.txt", b"hello world")},
            instance=instance,
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.file.name == "tests/test3.txt"

        # Instance can be edited w/out re-uploading the file and existing file
        # should be preserved.
        f = TextFileForm({"description": "New Description"}, instance=instance)
        f.fields["file"].required = False
        assert f.is_valid()
        instance = await f.asave()
        assert instance.description == "New Description"
        assert instance.file.name == "tests/test3.txt"

        # Delete the current file since this is not done by Django.
        await sync_to_async(instance.file.delete)()
        await instance.adelete()

    async def test_custom_file_field_save(self):
        """
        Regression for #11149: save_form_data should be called only once
        """

        class CFFForm(AsyncModelForm):
            class Meta:
                model = CustomFF
                fields = "__all__"

        # It's enough that the form saves without error -- the custom save routine will
        # generate an AssertionError if it is called more than once during save.
        form = CFFForm(data={"f": None})
        await form.asave()

    async def test_file_field_multiple_save(self):
        """
        Simulate a file upload and check how many times Model.save() gets
        called. Test for bug #639.
        """

        class PhotoForm(AsyncModelForm):
            class Meta:
                model = Photo
                fields = "__all__"

        # Grab an image for testing.
        filename = os.path.join(os.path.dirname(__file__), "test.png")
        with open(filename, "rb") as fp:
            img = fp.read()

        # Fake a POST QueryDict and FILES MultiValueDict.
        data = {"title": "Testing"}
        files = {"image": SimpleUploadedFile("test.png", img, "image/png")}

        form = PhotoForm(data=data, files=files)
        p = await form.asave()

        try:
            # Check the savecount stored on the object (see the model).
            assert p._savecount == 1
        finally:
            # Delete the "uploaded" file to avoid clogging /tmp.
            p = await Photo.objects.aget()
            await sync_to_async(p.image.delete)(save=False)

    def test_file_path_field_blank(self):
        """FilePathField(blank=True) includes the empty option."""

        class FPForm(AsyncModelForm):
            class Meta:
                model = FilePathModel
                fields = "__all__"

        form = FPForm()
        assert [name for _, name in form["path"].field.choices] == [
            "---------",
            "models.py",
        ]

    @pytest.mark.skipif(not test_images, reason="Pillow not installed")
    async def test_image_field(self):
        # ImageField and FileField are nearly identical, but they differ slightly when
        # it comes to validation. This specifically tests that #6302 is fixed for
        # both file fields and image fields.

        with open(os.path.join(os.path.dirname(__file__), "test.png"), "rb") as fp:
            image_data = fp.read()
        with open(os.path.join(os.path.dirname(__file__), "test2.png"), "rb") as fp:
            image_data2 = fp.read()

        f = ImageFileForm(
            data={"description": "An image"},
            files={"image": SimpleUploadedFile("test.png", image_data)},
        )
        assert f.is_valid()
        assert type(f.cleaned_data["image"]) is SimpleUploadedFile
        instance = await f.asave()
        assert instance.image.name == "tests/test.png"
        assert instance.width == 16
        assert instance.height == 16

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        f = ImageFileForm(
            data={"description": "An image"},
            files={"image": SimpleUploadedFile("test.png", image_data)},
        )
        assert f.is_valid()
        assert type(f.cleaned_data["image"]) is SimpleUploadedFile
        instance = await f.asave()
        assert instance.image.name == "tests/test.png"
        assert instance.width == 16
        assert instance.height == 16

        # Edit an instance that already has the (required) image defined in the
        # model. This will not save the image again, but leave it exactly as it
        # is.

        f = ImageFileForm(data={"description": "Look, it changed"}, instance=instance)
        assert f.is_valid()
        assert f.cleaned_data["image"].name == "tests/test.png"
        instance = await f.asave()
        assert instance.image.name == "tests/test.png"
        assert instance.height == 16
        assert instance.width == 16

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        # Override the file by uploading a new one.

        f = ImageFileForm(
            data={"description": "Changed it"},
            files={"image": SimpleUploadedFile("test2.png", image_data2)},
            instance=instance,
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "tests/test2.png"
        assert instance.height == 32
        assert instance.width == 48

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        await instance.adelete()

        f = ImageFileForm(
            data={"description": "Changed it"},
            files={"image": SimpleUploadedFile("test2.png", image_data2)},
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "tests/test2.png"
        assert instance.height == 32
        assert instance.width == 48

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        await instance.adelete()

        # Test the non-required ImageField
        # Note: In Oracle, we expect a null ImageField to return '' instead of
        # None.
        if connection.features.interprets_empty_strings_as_nulls:
            expected_null_imagefield_repr = ""
        else:
            expected_null_imagefield_repr = None

        f = OptionalImageFileForm(data={"description": "Test"})
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == expected_null_imagefield_repr
        assert instance.width is None
        assert instance.height is None

        f = OptionalImageFileForm(
            data={"description": "And a final one"},
            files={"image": SimpleUploadedFile("test3.png", image_data)},
            instance=instance,
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "tests/test3.png"
        assert instance.width == 16
        assert instance.height == 16

        # Editing the instance without re-uploading the image should not affect
        # the image or its width/height properties.
        f = OptionalImageFileForm({"description": "New Description"}, instance=instance)
        assert f.is_valid()
        instance = await f.asave()
        assert instance.description == "New Description"
        assert instance.image.name == "tests/test3.png"
        assert instance.width == 16
        assert instance.height == 16

        # Delete the current file since this is not done by Django.
        await sync_to_async(instance.image.delete)()
        await instance.adelete()

        f = OptionalImageFileForm(
            data={"description": "And a final one"},
            files={"image": SimpleUploadedFile("test4.png", image_data2)},
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "tests/test4.png"
        assert instance.width == 48
        assert instance.height == 32
        await instance.adelete()
        # Callable upload_to behavior that's dependent on the value of another
        # field in the model.
        f = ImageFileForm(
            data={"description": "And a final one", "path": "foo"},
            files={"image": SimpleUploadedFile("test4.png", image_data)},
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "foo/test4.png"
        await instance.adelete()

        # Editing an instance that has an image without an extension shouldn't
        # fail validation. First create:
        f = NoExtensionImageFileForm(
            data={"description": "An image"},
            files={"image": SimpleUploadedFile("test.png", image_data)},
        )
        assert f.is_valid()
        instance = await f.asave()
        assert instance.image.name == "tests/no_extension"
        # Then edit:
        f = NoExtensionImageFileForm(
            data={"description": "Edited image"}, instance=instance
        )
        assert f.is_valid()


class ModelOtherFieldTests(SimpleTestCase):
    def test_big_integer_field(self):
        bif = BigIntForm({"biggie": "-9223372036854775808"})
        self.assertTrue(bif.is_valid())
        bif = BigIntForm({"biggie": "-9223372036854775809"})
        self.assertFalse(bif.is_valid())
        self.assertEqual(
            bif.errors,
            {
                "biggie": [
                    "Ensure this value is greater than or equal to "
                    "-9223372036854775808."
                ]
            },
        )
        bif = BigIntForm({"biggie": "9223372036854775807"})
        self.assertTrue(bif.is_valid())
        bif = BigIntForm({"biggie": "9223372036854775808"})
        self.assertFalse(bif.is_valid())
        self.assertEqual(
            bif.errors,
            {
                "biggie": [
                    "Ensure this value is less than or equal to 9223372036854775807."
                ]
            },
        )

    def test_url_on_modelform(self):
        "Check basic URL field validation on model forms"

        class HomepageForm(AsyncModelForm):
            class Meta:
                model = Homepage
                fields = "__all__"

        self.assertFalse(HomepageForm({"url": "foo"}).is_valid())
        self.assertFalse(HomepageForm({"url": "http://"}).is_valid())
        self.assertFalse(HomepageForm({"url": "http://example"}).is_valid())
        self.assertFalse(HomepageForm({"url": "http://example."}).is_valid())
        self.assertFalse(HomepageForm({"url": "http://com."}).is_valid())

        self.assertTrue(HomepageForm({"url": "http://localhost"}).is_valid())
        self.assertTrue(HomepageForm({"url": "http://example.com"}).is_valid())
        self.assertTrue(HomepageForm({"url": "http://www.example.com"}).is_valid())
        self.assertTrue(HomepageForm({"url": "http://www.example.com:8000"}).is_valid())
        self.assertTrue(HomepageForm({"url": "http://www.example.com/test"}).is_valid())
        self.assertTrue(
            HomepageForm({"url": "http://www.example.com:8000/test"}).is_valid()
        )
        self.assertTrue(HomepageForm({"url": "http://example.com/foo/bar"}).is_valid())

    def test_modelform_non_editable_field(self):
        """
        When explicitly including a non-editable field in a ModelForm, the
        error message should be explicit.
        """
        # 'created', non-editable, is excluded by default
        self.assertNotIn("created", ArticleForm().fields)

        msg = (
            "'created' cannot be specified for Article model form as it is a "
            "non-editable field"
        )
        with self.assertRaisesMessage(FieldError, msg):

            class InvalidArticleForm(AsyncModelForm):
                class Meta:
                    model = Article
                    fields = ("headline", "created")

    def test_https_prefixing(self):
        """
        If the https:// prefix is omitted on form input, the field adds it
        again.
        """

        class HomepageForm(AsyncModelForm):
            # TODO: remove in django 6
            url = forms.URLField(assume_scheme="https")

            class Meta:
                model = Homepage
                fields = "__all__"

        form = HomepageForm({"url": "example.com"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["url"], "https://example.com")

        form = HomepageForm({"url": "example.com/test"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["url"], "https://example.com/test")


@pytest.mark.django_db(transaction=True)
class TestOtherModelForm:
    def test_media_on_modelform(self):
        # Similar to a regular Form class you can define custom media to be used on
        # the ModelForm.
        f = ModelFormWithMedia()
        assertHTMLEqual(
            str(f.media),
            '<link href="/some/form/css" media="all" rel="stylesheet">'
            '<script src="/some/form/javascript"></script>',
        )

    def test_choices_type(self):
        # Choices on CharField and IntegerField
        f = ArticleForm()
        with pytest.raises(ValidationError):
            f.fields["status"].clean("42")

        f = ArticleStatusForm()
        with pytest.raises(ValidationError):
            f.fields["status"].clean("z")

    def test_prefetch_related_queryset(self):
        """
        ModelChoiceField should respect a prefetch_related() on its queryset.
        """
        blue = Colour.objects.create(name="blue")
        red = Colour.objects.create(name="red")
        multicolor_item = ColourfulItem.objects.create()
        multicolor_item.colours.add(blue, red)
        red_item = ColourfulItem.objects.create()
        red_item.colours.add(red)

        class ColorModelChoiceField(forms.ModelChoiceField):
            def label_from_instance(self, obj):
                return ", ".join(c.name for c in obj.colours.all())

        field = ColorModelChoiceField(ColourfulItem.objects.prefetch_related("colours"))
        # CPython < 3.14 calls ModelChoiceField.__len__() when coercing to
        # tuple. PyPy and Python 3.14+ don't call __len__() and so .count()
        # isn't called on the QuerySet. The following would trigger an extra
        # query if prefetch were ignored.
        with assertNumQueries(2 if PYPY else 3):
            assert tuple(field.choices) == (
                ("", "---------"),
                (multicolor_item.pk, "blue, red"),
                (red_item.pk, "red"),
            )

    async def test_foreignkeys_which_use_to_field(self):
        apple = await Inventory.objects.acreate(barcode=86, name="Apple")
        pear = await Inventory.objects.acreate(barcode=22, name="Pear")
        core = await Inventory.objects.acreate(barcode=87, name="Core", parent=apple)

        field = forms.ModelChoiceField(Inventory.objects.all(), to_field_name="barcode")
        assert await sync_to_async(tuple)(field.choices) == (
            ("", "---------"),
            (86, "Apple"),
            (87, "Core"),
            (22, "Pear"),
        )

        form = InventoryForm(instance=core)
        assertHTMLEqual(
            await sync_to_async(str)(form["parent"]),
            """<select name="parent" id="id_parent">
<option value="">---------</option>
<option value="86" selected>Apple</option>
<option value="87">Core</option>
<option value="22">Pear</option>
</select>""",
        )
        data = model_to_dict(core)
        data["parent"] = "22"
        form = InventoryForm(data=data, instance=core)
        core = await form.asave()
        assert core.parent.name == "Pear"

        class CategoryForm(AsyncModelForm):
            description = forms.CharField()

            class Meta:
                model = Category
                fields = ["description", "url"]

        assert list(CategoryForm.base_fields) == ["description", "url"]

        assertHTMLEqual(
            await sync_to_async(str)(CategoryForm()),
            '<div><label for="id_description">Description:</label><input type="text" '
            'name="description" required id="id_description"></div><div>'
            '<label for="id_url">The URL:</label><input type="text" name="url" '
            'maxlength="40" required id="id_url"></div>',
        )
        # to_field_name should also work on ModelMultipleChoiceField ##################

        field = forms.ModelMultipleChoiceField(
            Inventory.objects.all(), to_field_name="barcode"
        )
        assert await sync_to_async(tuple)(field.choices) == (
            (86, "Apple"),
            (87, "Core"),
            (22, "Pear"),
        )
        assert list(await sync_to_async(field.clean)([86])) == [apple]

        form = SelectInventoryForm({"items": [87, 22]})
        assert await sync_to_async(form.is_valid)()
        assert len(form.cleaned_data) == 1
        assert list(form.cleaned_data["items"]) == [core, pear]

    def test_model_field_that_returns_none_to_exclude_itself_with_explicit_fields(self):
        assert list(CustomFieldForExclusionForm.base_fields) == ["name"]
        assertHTMLEqual(
            str(CustomFieldForExclusionForm()),
            '<div><label for="id_name">Name:</label><input type="text" '
            'name="name" maxlength="10" required id="id_name"></div>',
        )

    def test_iterable_model_m2m(self):
        class ColourfulItemForm(AsyncModelForm):
            class Meta:
                model = ColourfulItem
                fields = "__all__"

        colour = Colour.objects.create(name="Blue")
        form = ColourfulItemForm()
        self.maxDiff = 1024
        assertHTMLEqual(
            form.as_p(),
            """
            <p>
            <label for="id_name">Name:</label>
            <input id="id_name" type="text" name="name" maxlength="50" required></p>
            <p><label for="id_colours">Colours:</label>
            <select multiple name="colours" id="id_colours" required>
            <option value="%(blue_pk)s">Blue</option>
            </select></p>
            """
            % {"blue_pk": colour.pk},
        )

    def test_callable_field_default(self):
        class PublicationDefaultsForm(AsyncModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ("title", "date_published", "mode", "category")

        self.maxDiff = 2000
        form = PublicationDefaultsForm()
        today_str = str(datetime.date.today())
        assertHTMLEqual(
            form.as_p(),
            """
            <p><label for="id_title">Title:</label>
            <input id="id_title" maxlength="30" name="title" type="text" required>
            </p>
            <p><label for="id_date_published">Date published:</label>
            <input id="id_date_published" name="date_published" type="text" value="{0}"
                required>
            <input id="initial-id_date_published" name="initial-date_published"
                type="hidden" value="{0}">
            </p>
            <p><label for="id_mode">Mode:</label> <select id="id_mode" name="mode">
            <option value="di" selected>direct</option>
            <option value="de">delayed</option></select>
            <input id="initial-id_mode" name="initial-mode" type="hidden" value="di">
            </p>
            <p>
            <label for="id_category">Category:</label>
            <select id="id_category" name="category">
            <option value="1">Games</option>
            <option value="2">Comics</option>
            <option value="3" selected>Novel</option></select>
            <input id="initial-id_category" name="initial-category" type="hidden"
                value="3">
            """.format(
                today_str
            ),
        )
        empty_data = {
            "title": "",
            "date_published": today_str,
            "initial-date_published": today_str,
            "mode": "di",
            "initial-mode": "di",
            "category": "3",
            "initial-category": "3",
        }
        bound_form = PublicationDefaultsForm(empty_data)
        assert bound_form.has_changed() is False


class ModelFormCustomErrorTests(SimpleTestCase):
    def test_custom_error_messages(self):
        data = {"name1": "@#$!!**@#$", "name2": "@#$!!**@#$"}
        errors = CustomErrorMessageForm(data).errors
        self.assertHTMLEqual(
            str(errors["name1"]),
            '<ul class="errorlist">' "<li>Form custom error message.</li></ul>",
        )
        self.assertHTMLEqual(
            str(errors["name2"]),
            '<ul class="errorlist">' "<li>Model custom error message.</li></ul>",
        )

    def test_model_clean_error_messages(self):
        data = {"name1": "FORBIDDEN_VALUE", "name2": "ABC"}
        form = CustomErrorMessageForm(data)
        self.assertFalse(form.is_valid())
        self.assertHTMLEqual(
            str(form.errors["name1"]),
            '<ul class="errorlist">' "<li>Model.clean() error messages.</li></ul>",
        )
        data = {"name1": "FORBIDDEN_VALUE2", "name2": "ABC"}
        form = CustomErrorMessageForm(data)
        self.assertFalse(form.is_valid())
        self.assertHTMLEqual(
            str(form.errors["name1"]),
            '<ul class="errorlist">'
            "<li>Model.clean() error messages (simpler syntax).</li></ul>",
        )
        data = {"name1": "GLOBAL_ERROR", "name2": "ABC"}
        form = CustomErrorMessageForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["__all__"], ["Global error message."])


@pytest.mark.django_db
class TestCustomClean:
    def test_override_clean(self):
        """
        Regression for #12596: Calling super from ModelForm.clean() should be
        optional.
        """

        class TripleFormWithCleanOverride(AsyncModelForm):
            class Meta:
                model = Triple
                fields = "__all__"

            def clean(self):
                if not self.cleaned_data["left"] == self.cleaned_data["right"]:
                    raise ValidationError("Left and right should be equal")
                return self.cleaned_data

        form = TripleFormWithCleanOverride({"left": 1, "middle": 2, "right": 1})
        assert form.is_valid()
        # form.instance.left will be None if the instance was not constructed
        # by form.full_clean().
        assert form.instance.left == 1

    async def test_model_form_clean_applies_to_model(self):
        """
        Regression test for #12960. Make sure the cleaned_data returned from
        ModelForm.clean() is applied to the model instance.
        """

        class CategoryForm(AsyncModelForm):
            class Meta:
                model = Category
                fields = "__all__"

            def clean(self):
                self.cleaned_data["name"] = self.cleaned_data["name"].upper()
                return self.cleaned_data

        data = {"name": "Test", "slug": "test", "url": "/test"}
        form = CategoryForm(data)
        category = await form.asave()
        assert category.name == "TEST"


class ModelFormInheritanceTests(SimpleTestCase):
    def test_form_subclass_inheritance(self):
        class Form(forms.Form):
            age = forms.IntegerField()

        class ModelForm(AsyncModelForm, Form):
            class Meta:
                model = Writer
                fields = "__all__"

        self.assertEqual(list(ModelForm().fields), ["name", "age"])

    def test_field_removal(self):
        class ModelForm(AsyncModelForm):
            class Meta:
                model = Writer
                fields = "__all__"

        class Mixin:
            age = None

        class Form(forms.Form):
            age = forms.IntegerField()

        class Form2(forms.Form):
            foo = forms.IntegerField()

        self.assertEqual(list(ModelForm().fields), ["name"])
        self.assertEqual(list(type("NewForm", (Mixin, Form), {})().fields), [])
        self.assertEqual(
            list(type("NewForm", (Form2, Mixin, Form), {})().fields), ["foo"]
        )
        self.assertEqual(
            list(type("NewForm", (Mixin, ModelForm, Form), {})().fields), ["name"]
        )
        self.assertEqual(
            list(type("NewForm", (ModelForm, Mixin, Form), {})().fields), ["name"]
        )
        self.assertEqual(
            list(type("NewForm", (ModelForm, Form, Mixin), {})().fields),
            ["name", "age"],
        )
        self.assertEqual(
            list(type("NewForm", (ModelForm, Form), {"age": None})().fields), ["name"]
        )

    def test_field_removal_name_clashes(self):
        """
        Form fields can be removed in subclasses by setting them to None
        (#22510).
        """

        class MyForm(AsyncModelForm):
            media = forms.CharField()

            class Meta:
                model = Writer
                fields = "__all__"

        class SubForm(MyForm):
            media = None

        self.assertIn("media", MyForm().fields)
        self.assertNotIn("media", SubForm().fields)
        self.assertTrue(hasattr(MyForm, "media"))
        self.assertTrue(hasattr(SubForm, "media"))


class StumpJokeForm(AsyncModelForm):
    class Meta:
        model = StumpJoke
        fields = "__all__"


class CustomFieldWithQuerysetButNoLimitChoicesTo(forms.Field):
    queryset = 42


class StumpJokeWithCustomFieldForm(AsyncModelForm):
    custom = CustomFieldWithQuerysetButNoLimitChoicesTo()

    class Meta:
        model = StumpJoke
        fields = ()


class LimitChoicesToTests(TestCase):
    """
    Tests the functionality of ``limit_choices_to``.
    """

    @classmethod
    def setUpTestData(cls):
        cls.threepwood = Character.objects.create(
            username="threepwood",
            last_action=datetime.datetime.today() + datetime.timedelta(days=1),
        )
        cls.marley = Character.objects.create(
            username="marley",
            last_action=datetime.datetime.today() - datetime.timedelta(days=1),
        )

    def test_limit_choices_to_callable_for_fk_rel(self):
        """
        A ForeignKey can use limit_choices_to as a callable (#2554).
        """
        stumpjokeform = StumpJokeForm()
        self.assertSequenceEqual(
            stumpjokeform.fields["most_recently_fooled"].queryset, [self.threepwood]
        )

    def test_limit_choices_to_callable_for_m2m_rel(self):
        """
        A ManyToManyField can use limit_choices_to as a callable (#2554).
        """
        stumpjokeform = StumpJokeForm()
        self.assertSequenceEqual(
            stumpjokeform.fields["most_recently_fooled"].queryset, [self.threepwood]
        )

    def test_custom_field_with_queryset_but_no_limit_choices_to(self):
        """
        A custom field with a `queryset` attribute but no `limit_choices_to`
        works (#23795).
        """
        f = StumpJokeWithCustomFieldForm()
        self.assertEqual(f.fields["custom"].queryset, 42)

    def test_fields_for_model_applies_limit_choices_to(self):
        fields = fields_for_model(StumpJoke, ["has_fooled_today"])
        self.assertSequenceEqual(fields["has_fooled_today"].queryset, [self.threepwood])

    def test_callable_called_each_time_form_is_instantiated(self):
        field = StumpJokeForm.base_fields["most_recently_fooled"]
        with mock.patch.object(field, "limit_choices_to") as today_callable_dict:
            StumpJokeForm()
            self.assertEqual(today_callable_dict.call_count, 1)
            StumpJokeForm()
            self.assertEqual(today_callable_dict.call_count, 2)
            StumpJokeForm()
            self.assertEqual(today_callable_dict.call_count, 3)

    @isolate_apps("test_model_forms")
    def test_limit_choices_to_no_duplicates(self):
        joke1 = StumpJoke.objects.create(
            funny=True,
            most_recently_fooled=self.threepwood,
        )
        joke2 = StumpJoke.objects.create(
            funny=True,
            most_recently_fooled=self.threepwood,
        )
        joke3 = StumpJoke.objects.create(
            funny=True,
            most_recently_fooled=self.marley,
        )
        StumpJoke.objects.create(funny=False, most_recently_fooled=self.marley)
        joke1.has_fooled_today.add(self.marley, self.threepwood)
        joke2.has_fooled_today.add(self.marley)
        joke3.has_fooled_today.add(self.marley, self.threepwood)

        class CharacterDetails(models.Model):
            character1 = models.ForeignKey(
                Character,
                models.CASCADE,
                limit_choices_to=models.Q(
                    jokes__funny=True,
                    jokes_today__funny=True,
                ),
                related_name="details_fk_1",
            )
            character2 = models.ForeignKey(
                Character,
                models.CASCADE,
                limit_choices_to={
                    "jokes__funny": True,
                    "jokes_today__funny": True,
                },
                related_name="details_fk_2",
            )
            character3 = models.ManyToManyField(
                Character,
                limit_choices_to=models.Q(
                    jokes__funny=True,
                    jokes_today__funny=True,
                ),
                related_name="details_m2m_1",
            )

        class CharacterDetailsForm(AsyncModelForm):
            class Meta:
                model = CharacterDetails
                fields = "__all__"

        form = CharacterDetailsForm()
        self.assertCountEqual(
            form.fields["character1"].queryset,
            [self.marley, self.threepwood],
        )
        self.assertCountEqual(
            form.fields["character2"].queryset,
            [self.marley, self.threepwood],
        )
        self.assertCountEqual(
            form.fields["character3"].queryset,
            [self.marley, self.threepwood],
        )

    def test_limit_choices_to_m2m_through(self):
        class DiceForm(AsyncModelForm):
            class Meta:
                model = Dice
                fields = ["numbers"]

        Number.objects.create(value=0)
        n1 = Number.objects.create(value=1)
        n2 = Number.objects.create(value=2)

        form = DiceForm()
        self.assertCountEqual(form.fields["numbers"].queryset, [n1, n2])


class FormFieldCallbackTests(SimpleTestCase):
    def test_baseform_with_widgets_in_meta(self):
        """
        Using base forms with widgets defined in Meta should not raise errors.
        """
        widget = forms.Textarea()

        class BaseForm(AsyncModelForm):
            class Meta:
                model = Person
                widgets = {"name": widget}
                fields = "__all__"

        Form = modelform_factory(Person, form=BaseForm)
        self.assertIsInstance(Form.base_fields["name"].widget, forms.Textarea)

    def test_factory_with_widget_argument(self):
        """Regression for #15315: modelform_factory should accept widgets
        argument
        """
        widget = forms.Textarea()

        # Without a widget should not set the widget to textarea
        Form = modelform_factory(Person, fields="__all__", form=AsyncModelForm)
        self.assertNotEqual(Form.base_fields["name"].widget.__class__, forms.Textarea)

        # With a widget should not set the widget to textarea
        Form = modelform_factory(
            Person, fields="__all__", widgets={"name": widget}, form=AsyncModelForm
        )
        self.assertEqual(Form.base_fields["name"].widget.__class__, forms.Textarea)

    def test_modelform_factory_without_fields(self):
        """Regression for #19733"""
        message = (
            "Calling modelform_factory without defining 'fields' or 'exclude' "
            "explicitly is prohibited."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            modelform_factory(Person, form=AsyncModelForm)

    def test_modelform_factory_with_all_fields(self):
        """Regression for #19733"""
        form = modelform_factory(Person, fields="__all__", form=AsyncModelForm)
        self.assertEqual(list(form.base_fields), ["name"])

    def test_custom_callback(self):
        """A custom formfield_callback is used if provided"""
        callback_args = []

        def callback(db_field, **kwargs):
            callback_args.append((db_field, kwargs))
            return db_field.formfield(**kwargs)

        widget = forms.Textarea()

        class BaseForm(AsyncModelForm):
            class Meta:
                model = Person
                widgets = {"name": widget}
                fields = "__all__"

        modelform_factory(Person, form=BaseForm, formfield_callback=callback)
        id_field, name_field = Person._meta.fields

        self.assertEqual(
            callback_args, [(id_field, {}), (name_field, {"widget": widget})]
        )

    def test_bad_callback(self):
        # A bad callback provided by user still gives an error
        with self.assertRaises(TypeError):
            modelform_factory(
                Person,
                fields="__all__",
                formfield_callback="not a function or callable",
                form=AsyncModelForm,
            )

    def test_inherit_after_custom_callback(self):
        def callback(db_field, **kwargs):
            if isinstance(db_field, models.CharField):
                return forms.CharField(widget=forms.Textarea)
            return db_field.formfield(**kwargs)

        class BaseForm(AsyncModelForm):
            class Meta:
                model = Person
                fields = "__all__"

        NewForm = modelform_factory(Person, form=BaseForm, formfield_callback=callback)

        class InheritedForm(NewForm):
            pass

        for name in NewForm.base_fields:
            self.assertEqual(
                type(InheritedForm.base_fields[name].widget),
                type(NewForm.base_fields[name].widget),
            )

    def test_custom_callback_in_meta(self):
        def callback(db_field, **kwargs):
            return forms.CharField(widget=forms.Textarea)

        class NewForm(AsyncModelForm):
            class Meta:
                model = Person
                fields = ["id", "name"]
                formfield_callback = callback

        for field in NewForm.base_fields.values():
            self.assertEqual(type(field.widget), forms.Textarea)

    def test_custom_callback_from_base_form_meta(self):
        def callback(db_field, **kwargs):
            return forms.CharField(widget=forms.Textarea)

        class BaseForm(AsyncModelForm):
            class Meta:
                model = Person
                fields = "__all__"
                formfield_callback = callback

        NewForm = modelform_factory(model=Person, form=BaseForm)

        class InheritedForm(NewForm):
            pass

        for name, field in NewForm.base_fields.items():
            self.assertEqual(type(field.widget), forms.Textarea)
            self.assertEqual(
                type(field.widget),
                type(InheritedForm.base_fields[name].widget),
            )


class LocalizedModelFormTest(TestCase):
    def test_model_form_applies_localize_to_some_fields(self):
        class PartiallyLocalizedTripleForm(AsyncModelForm):
            class Meta:
                model = Triple
                localized_fields = (
                    "left",
                    "right",
                )
                fields = "__all__"

        f = PartiallyLocalizedTripleForm({"left": 10, "middle": 10, "right": 10})
        self.assertTrue(f.is_valid())
        self.assertTrue(f.fields["left"].localize)
        self.assertFalse(f.fields["middle"].localize)
        self.assertTrue(f.fields["right"].localize)

    def test_model_form_applies_localize_to_all_fields(self):
        class FullyLocalizedTripleForm(AsyncModelForm):
            class Meta:
                model = Triple
                localized_fields = "__all__"
                fields = "__all__"

        f = FullyLocalizedTripleForm({"left": 10, "middle": 10, "right": 10})
        self.assertTrue(f.is_valid())
        self.assertTrue(f.fields["left"].localize)
        self.assertTrue(f.fields["middle"].localize)
        self.assertTrue(f.fields["right"].localize)

    def test_model_form_refuses_arbitrary_string(self):
        msg = (
            "BrokenLocalizedTripleForm.Meta.localized_fields "
            "cannot be a string. Did you mean to type: ('foo',)?"
        )
        with self.assertRaisesMessage(TypeError, msg):

            class BrokenLocalizedTripleForm(AsyncModelForm):
                class Meta:
                    model = Triple
                    localized_fields = "foo"


class CustomMetaclass(ModelFormMetaclass):
    def __new__(cls, name, bases, attrs):
        new = super().__new__(cls, name, bases, attrs)
        new.base_fields = {}
        return new


class CustomMetaclassForm(AsyncModelForm, metaclass=CustomMetaclass):
    pass


class CustomMetaclassTestCase(SimpleTestCase):
    def test_modelform_factory_metaclass(self):
        new_cls = modelform_factory(Person, fields="__all__", form=CustomMetaclassForm)
        self.assertEqual(new_cls.base_fields, {})


class StrictAssignmentTests(SimpleTestCase):
    """
    Should a model do anything special with __setattr__() or descriptors which
    raise a ValidationError, a model form should catch the error (#24706).
    """

    def test_setattr_raises_validation_error_field_specific(self):
        """
        A model ValidationError using the dict form should put the error
        message into the correct key of form.errors.
        """
        form_class = modelform_factory(
            model=StrictAssignmentFieldSpecific, fields=["title"], form=AsyncModelForm
        )
        form = form_class(data={"title": "testing setattr"}, files=None)
        # This line turns on the ValidationError; it avoids the model erroring
        # when its own __init__() is called when creating form.instance.
        form.instance._should_error = True
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {"title": ["Cannot set attribute", "This field cannot be blank."]},
        )

    def test_setattr_raises_validation_error_non_field(self):
        """
        A model ValidationError not using the dict form should put the error
        message into __all__ (i.e. non-field errors) on the form.
        """
        form_class = modelform_factory(
            model=StrictAssignmentAll, fields=["title"], form=AsyncModelForm
        )
        form = form_class(data={"title": "testing setattr"}, files=None)
        # This line turns on the ValidationError; it avoids the model erroring
        # when its own __init__() is called when creating form.instance.
        form.instance._should_error = True
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                "__all__": ["Cannot set attribute"],
                "title": ["This field cannot be blank."],
            },
        )


class ModelToDictTests(TestCase):
    def test_many_to_many(self):
        """Data for a ManyToManyField is a list rather than a lazy QuerySet."""
        blue = Colour.objects.create(name="blue")
        red = Colour.objects.create(name="red")
        item = ColourfulItem.objects.create()
        item.colours.set([blue])
        data = model_to_dict(item)["colours"]
        self.assertEqual(data, [blue])
        item.colours.set([red])
        # If data were a QuerySet, it would be reevaluated here and give "red"
        # instead of the original value.
        self.assertEqual(data, [blue])
