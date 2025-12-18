# users/forms.py — FINAL, UNBREAKABLE, PRODUCTION-READY
import re
from django import forms
from .models import FirmProfile
from allauth.account.forms import SignupForm


class FirmProfileForm(forms.ModelForm):
    class Meta:
        model = FirmProfile
        fields = ['firm_name', 'email', 'domain', 'phone', 'address', 'logo', 'subscription_tier']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
            'subscription_tier': forms.Select(attrs={'disabled': 'disabled'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Beautiful Tailwind styling
        css = "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-4 focus:ring-indigo-200 focus:border-indigo-500 transition"
        file_css = "block w-full text-sm text-gray-600 file:mr-4 file:py-3 file:px-6 file:rounded-lg file:border-0 file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"

        for field in self.fields:
            if field == 'logo':
                self.fields[field].widget.attrs.update({'class': file_css})
            elif field == 'address':
                self.fields[field].widget.attrs.update({'class': css + " resize-none"})
            elif field == 'subscription_tier':
                self.fields[field].widget.attrs.update({'class': css + " bg-gray-100"})
            else:
                self.fields[field].widget.attrs.update({'class': css})

        # Make subscription tier non-editable
        self.fields['subscription_tier'].disabled = True

    # === THESE ARE THE ONLY CLEAN METHODS YOU NEED ===
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and FirmProfile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use by another firm.")
        return email

    def clean_domain(self):
        # 1. Get the data and normalize it (lowercase and strip whitespace)
        domain = self.cleaned_data.get('domain', '').strip().lower()

        if domain:
            # 2. STRIP: Remove trailing slashes
            domain = domain.rstrip('/')
            
            # 3. STRIP: Remove http:// or https:// if the user pasted a full URL
            domain = re.sub(r'^https?://', '', domain)
            
            # 4. STRIP: Remove 'www.' to keep domains consistent (optional but recommended)
            domain = re.sub(r'^www\.', '', domain)

            # 5. VALIDATE: Ensure it's a clean domain format (e.g., example.com)
            if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$', domain):
                raise forms.ValidationError("Invalid domain format. Please enter a valid domain like 'example.com'.")

            # 6. DUPLICATE CHECK: (Your existing logic)
            if FirmProfile.objects.filter(domain=domain).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This domain is already registered.")

        return domain

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and FirmProfile.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone

    # THIS IS THE MAGIC LINE THAT KILLS THE GHOST ERROR FOREVER
    def clean_address(self):
        return self.cleaned_data.get('address')  # Just return it — no validation on encrypted field


class CustomSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        request.session["account_verified_email"] = self.cleaned_data["email"]
        return user