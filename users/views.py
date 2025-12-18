# users/views.py — SAFE & FINAL
from django.views.generic import TemplateView, UpdateView, CreateView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from allauth.account.views import SignupView
from .models import FirmProfile, UserAccount
from .forms import FirmProfileForm
import json
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import secrets
import string
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


# -----------------------------
# PROFILE VIEWS
# -----------------------------
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firm'] = getattr(self.request.user, 'firm', None)
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = UserAccount
    fields = ['first_name', 'last_name']
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


# -----------------------------
# FIRM VIEWS
# -----------------------------
class FirmSettingsView(LoginRequiredMixin, UpdateView):
    model = FirmProfile
    form_class = FirmProfileForm
    template_name = 'users/firm_settings.html'
    success_url = reverse_lazy('users:firm_settings')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')

        if not hasattr(request.user, 'firmprofile'):
            messages.warning(request, "Please set up your firm first.")
            return redirect("users:firm_wizard")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.firmprofile

    def form_valid(self, form):
        messages.success(self.request, "Firm settings saved.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class FirmSetupWizardView(LoginRequiredMixin, CreateView):
    model = FirmProfile
    form_class = FirmProfileForm
    template_name = 'users/firm_wizard.html'
    success_url = reverse_lazy('dashboard:home')

    def get(self, request, *args, **kwargs):
        messages.get_messages(request).used = True  # Clear stale warnings
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        firm = form.save(commit=False)
        firm.user = self.request.user
        firm.save()

        self.request.user.firm = firm
        self.request.user.save()

        messages.success(self.request, f"Welcome to {firm.firm_name}! Your firm is ready.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_wizard'] = True
        return context


# -----------------------------
# DASHBOARD REDIRECT
# -----------------------------
class DashboardRedirectView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        if not hasattr(request.user, 'firm') or request.user.firm is None:
            return redirect('users:firm_wizard')
        return redirect('dashboard:home')


# -----------------------------
# SIGNUP VIEWS
# -----------------------------
class SignupWizardView(FormView):
    template_name = 'users/signup.html'
    success_url = reverse_lazy('dashboard:home')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return redirect('account_signup')


class CustomSignupView(SignupView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Check your inbox! We sent a confirmation link to your email. Click it to activate your account."
        )
        return render(self.request, "account/signup.html", self.get_context_data(form=form))


class EmailConfirmationSentView(TemplateView):
    template_name = "account/email_confirmation_sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get("account_verified_email", "your inbox")
        return context


# -----------------------------
# ADMIN HELPER (DEBUG ONLY)
# -----------------------------
def create_admin_user(request):
    if not settings.DEBUG:
        return HttpResponse("Not allowed.", status=403)

    User = get_user_model()
    username = "admin"
    email = "complylaw@alhambra-solutions.com"
    password = "1234abcd@dmin"

    if User.objects.filter(username=username).exists():
        return HttpResponse("Admin user already exists.")

    User.objects.create_superuser(username=username, email=email, password=password)
    return HttpResponse(f"Superuser '{username}' created successfully!")


# -----------------------------
# FIRM LOGO CLEAR
# -----------------------------
class ClearFirmLogoView(LoginRequiredMixin, View):
    def post(self, request):
        profile = getattr(request.user, 'firmprofile', None)
        if profile and profile.logo:
            profile.logo.delete(save=False)
            profile.logo = None
            profile.save()
            messages.success(request, "Firm logo removed successfully.")
        return HttpResponse("""
            <div class="p-5 bg-gray-50 rounded-xl border border-gray-200 text-center text-gray-500 text-sm">
                No logo uploaded
            </div>
        """)
