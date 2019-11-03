from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class UserMiniProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mini_user_profile', primary_key=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    alloted_institute_code = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=1, blank=True, null=True)
    email = models.CharField(max_length=40, blank=True, null=True)
    contact_number = models.CharField(max_length=40, blank=True, null=True)
    is_staff = models.BooleanField(blank=True)

