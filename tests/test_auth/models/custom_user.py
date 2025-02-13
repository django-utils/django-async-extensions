from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from django.db import models


# The custom user uses email as the unique identifier, and requires
# that every user provide a date of birth. This lets us test
# changes in username datatype, and non-text required fields.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, date_of_birth, password=None, **fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email), date_of_birth=date_of_birth, **fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    async def acreate_user(self, email, date_of_birth, password=None, **fields):
        """See create_user()"""
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email), date_of_birth=date_of_birth, **fields
        )

        user.set_password(password)
        await user.asave(using=self._db)
        return user

    def create_superuser(self, email, password, date_of_birth, **fields):
        u = self.create_user(
            email, password=password, date_of_birth=date_of_birth, **fields
        )
        u.is_admin = True
        u.save(using=self._db)
        return u


class CustomUser(AbstractBaseUser):
    email = models.EmailField(verbose_name="email address", max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    date_of_birth = models.DateField()
    first_name = models.CharField(max_length=50)

    custom_objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["date_of_birth", "first_name"]

    def __str__(self):
        return self.email

    # Maybe required?
    def get_group_permissions(self, obj=None):
        return set()

    def get_all_permissions(self, obj=None):
        return set()

    def has_perm(self, perm, obj=None):
        return True

    def has_perms(self, perm_list, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    # Admin required fields
    @property
    def is_staff(self):
        return self.is_admin
