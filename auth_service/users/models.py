from email.policy import default

from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password, **extra_fields):
        if username is None:
            raise ValueError("Username is required.")
        if email is None:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("is_staff must be true.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("is_superuser must be true.")
        
        user = self.create_user(username=username, email=email, password=password, **extra_fields)
        return user
        
class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    username = models.CharField(max_length=150, blank=False, null=False, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    otp = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set'
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    objects = CustomUserManager()

    def __str__(self):
        return f'{self.username} - {self.email}'
    

class Contact(models.Model):
    STATUS_CHOICE = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("blocked", "Blocked")
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, related_name='contact', on_delete=models.CASCADE)
    contact = models.ForeignKey(CustomUser, related_name='related_to', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICE, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'contact')

    def __str__(self):
        return f"{self.user.username} ↔ {self.contact.username} ({self.status})"
    


    