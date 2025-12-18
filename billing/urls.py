# billing/urls.py
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path("", views.pricing, name="pricing"),
    path("create-checkout/", views.create_checkout, name="create_checkout"),
    path("success/", views.success, name="success"),
    #path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("test-email/", views.test_email_diagnostic),
]