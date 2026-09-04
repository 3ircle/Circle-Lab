from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    
    class Meta:
        db_table = 'user_table'
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'