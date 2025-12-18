import stripe
import logging
import sys
import secrets
import string

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from allauth.account.models import EmailAddress

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)
User = get_user_model()

def generate_random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(chars) for _ in range(length))

# ------------------------------------------------------------------
# Pricing Page
# ------------------------------------------------------------------
def pricing(request):
    return render(request, "billing/pricing.html")

# ------------------------------------------------------------------
# Create Checkout Session
# ------------------------------------------------------------------
def create_checkout(request):
    if request.method != "POST":
        return redirect("pricing")

    email = request.POST.get("email")
    plan = request.POST.get("plan", "pro")

    if not email:
        return JsonResponse({"error": "Email is required"}, status=400)

    price_id = settings.STRIPE_PRICE_PRO if plan == "pro" else settings.STRIPE_PRICE_BASIC

    DOMAIN = settings.SITE_DOMAIN
    protocol = "http" if DOMAIN.startswith("localhost") else "https"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{protocol}://{DOMAIN}/billing/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{protocol}://{DOMAIN}/pricing/",
        )
        return redirect(session.url, code=303)
    except Exception as e:
        logger.exception("Stripe checkout error")
        return JsonResponse({"error": str(e)}, status=400)

# ------------------------------------------------------------------
# Stripe Webhook (SOURCE OF TRUTH)
# ------------------------------------------------------------------
@csrf_exempt
def stripe_webhook(request):
    print("DEBUG: Webhook received!", file=sys.stderr)
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Webhook signature/payload error: {e}")
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not email or not subscription_id:
            logger.error("Missing email or subscription ID in Stripe session")
            return HttpResponse(status=400)

        # Idempotency Checks
        if User.objects.filter(stripe_subscription_id=subscription_id).exists():
            return HttpResponse(status=200)

        if User.objects.filter(email=email).exists():
            return HttpResponse(status=200)

        try:
            with transaction.atomic():
                password = generate_random_password()
                username = email.split("@")[0]

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                user.save()

                EmailAddress.objects.create(
                    user=user, email=email, verified=True, primary=True
                )

                def send_welcome_email():
                    print(f"DEBUG: Transaction committed. Sending email to {email}...", file=sys.stderr)
                    
                    # Professional Email Body
                    subject = "Welcome to ComplyLaw – Your Account is Ready"
                    message = f"""
                Dear User,

                Thank you for choosing ComplyLaw! Your subscription is now active, and your account has been successfully created.

                Below are your temporary login credentials:

                --------------------------------------------------
                
                Login Email: {email}
                Temporary Password: {password}
                
                Login URL: https://{settings.SITE_DOMAIN}/accounts/login/
                
                --------------------------------------------------

                For security reasons, we recommend that you change your password immediately after your first login via the Account Settings page.

                If you have any questions or need assistance getting started, simply reply to this email.

                Best regards,
                The ComplyLaw Team
                
                    """

                    try:
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        print(f"DEBUG: Professional email accepted by SendGrid for {email}", file=sys.stderr)
                    except Exception as e:
                        logger.error(f"Post-commit email failure: {e}")

                transaction.on_commit(send_welcome_email)

        except Exception:
            logger.exception("Failed to process user creation")
            return HttpResponse(status=500)

    return HttpResponse(status=200)

# ------------------------------------------------------------------
# Success Page
# ------------------------------------------------------------------
def success(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard/home.html')
    return render(request, "billing/success.html")
    
    
    
# billing/views.py

def test_email_diagnostic(request):
    from django.core.mail import get_connection, send_mail
    from django.conf import settings
    import os

    results = []
    
    # Check Environment
    results.append(f"RENDER Env Var: {os.getenv('RENDER')}")
    results.append(f"From Email: {settings.DEFAULT_FROM_EMAIL}")
    
    # Check Backend
    conn = get_connection()
    backend_name = f"{conn.__class__.__module__}.{conn.__class__.__name__}"
    results.append(f"Active Backend: {backend_name}")

    # Try Sending
    try:
        send_mail(
            "Diagnostic Test",
            "Checking SendGrid connectivity from Render Free Tier.",
            settings.DEFAULT_FROM_EMAIL,
            ["complylawtestuser29@yopmail.com"],
            fail_silently=False
        )
        results.append("✅ SUCCESS: SendGrid accepted the email request.")
    except Exception as e:
        results.append(f"❌ ERROR: {type(e).__name__} - {str(e)}")

    return HttpResponse("<br>".join(results))