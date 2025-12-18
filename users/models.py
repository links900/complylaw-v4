# users/models.py (COMPLETE)
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField
from django.core.serializers.json import DjangoJSONEncoder
import json
from auditlog.registry import auditlog
from django.conf import settings
from django.core.validators import RegexValidator


class FirmProfile(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    firm_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    domain = models.CharField(max_length=255, unique=True)
    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        validators=[RegexValidator(r'^\+?\d{7,15}$', 'Enter a valid phone number.')],
        help_text="e.g +18881234567"
    )
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    address = EncryptedTextField(blank=True)
    
    
    user = models.OneToOneField(
        #User,
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='firmprofile'  # ← THIS IS KEY
    )
    
    # Encrypted JSON
    _preferences = EncryptedTextField(blank=True, default='{}')
    
    subscription_tier = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='trial')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.firm_name

    class Meta:
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['email']),
        ]

    # JSON Property
    def get_preferences(self):
        return json.loads(self._preferences) if self._preferences else {}
    def set_preferences(self, value):
        self._preferences = json.dumps(value, cls=DjangoJSONEncoder)
    preferences = property(get_preferences, set_preferences)


# users/models.py (ONLY CHANGE THIS LINE)
class UserAccount(AbstractUser):
    ROLE_CHOICES = [('owner', 'Owner'), ('viewer', 'Viewer')]
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    firm = models.ForeignKey(
        FirmProfile,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,      # ← ADD THIS
        blank=True      # ← ADD THIS
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    mfa_secret = EncryptedCharField(max_length=255, null=True, blank=True)
    last_scan_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.email} ({self.role} @ {self.firm.firm_name if self.firm else 'No Firm'})"

auditlog.register(FirmProfile)
auditlog.register(UserAccount)