from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'photographer'),
        (2, 'customer'),
    )

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=2)
    REQUIRED_FIELDS = []

    objects = CustomUserManager()


class CustomUserProfile(models.Model):
    user = models.OneToOneField(CustomUser, primary_key=True, on_delete=models.CASCADE, related_name='user')
    ssn = models.CharField(max_length=13, blank=True, default="")
    bank_account_number = models.CharField(max_length=50, blank=True, default="")
    bank_name = models.CharField(max_length=50, blank=True, default="")
    bank_account_name = models.CharField(max_length=50, blank=True, default="")
    phone = models.CharField(max_length=11, blank=True, default="")


    def __str__(self):
        return self.user.username
    
    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

