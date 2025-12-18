# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import public_home
from users.views import CustomSignupView
from billing import views as billing_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),

    # Allauth signup/login
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('accounts/', include('allauth.urls')),

    # App URLs
    #path('pricing/', include('billing.urls', namespace='billing')),
    path('billing/', include('billing.urls', namespace='billing')),
    
    #path('profile/', include('users.urls')),
    path('', public_home, name='home'),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('scanner/', include('scanner.urls')),
    path('reports/', include('reports.urls')),
    path('checklists/', include('checklists.urls', namespace='checklists')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
