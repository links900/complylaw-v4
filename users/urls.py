# users/urls.py — FINAL & PERFECT VERSION
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from . import views
from users.views import ClearFirmLogoView

app_name = 'users'

urlpatterns = [
    # CORRECT: These now work at /profile/ and /profile/edit/
    path('', views.ProfileView.as_view(), name='profile'),
    path('edit/', views.ProfileEditView.as_view(), name='profile_edit'),

    # Firm settings
    path('firm/', views.FirmSettingsView.as_view(), name='firm_settings'),
    path('firm/wizard/', views.FirmSetupWizardView.as_view(), name='firm_wizard'),
    path('clear-firm-logo/', ClearFirmLogoView.as_view(), name='clear_firm_logo'),
    

    # Optional: custom login/logout (you can keep or remove)
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="logout",
    ),

    # Remove these — they conflict or are unused
    # path('signup/', views.SignupWizardView.as_view(), name='signup'),
    # path('', views.DashboardRedirectView.as_view(), name='root'),
    # path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path('create-admin/', views.create_admin_user, name='create_admin'),
    

   
]