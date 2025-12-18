# core/settings.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# ========================= DEBUG PRINT =========================
print("DEBUG SETTINGS LOADED", file=sys.stderr)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "fallback_dev_secret_key")

# ========================= LOAD ENV =========================
# Load .env locally only
if not os.getenv('RENDER'):
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ========================= DEBUG / ALLOWED HOSTS =========================
if os.getenv('RENDER'):
    #DEBUG = False
    DEBUG = os.getenv("DEBUG", "False") == "True"
   
    ALLOWED_HOSTS = ['complylaw-v1.onrender.com', '.onrender.com']

    CSRF_TRUSTED_ORIGINS = [
        'https://complylaw-v1.onrender.com',
        'https://*.onrender.com',   # covers future services like complylaw-v2, etc.
    ]

    # Optional but recommended in production
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000      # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]

# ========================= DATABASE =========================
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# ========================= FIELD ENCRYPTION KEY =========================
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')
print("FIELD_ENCRYPTION_KEY:", FIELD_ENCRYPTION_KEY, file=sys.stderr)

if os.getenv('RENDER'):
    if not FIELD_ENCRYPTION_KEY:
        raise ValueError("FIELD_ENCRYPTION_KEY is missing in Render Environment Variables!")
    try:
        from cryptography.fernet import Fernet
        Fernet(FIELD_ENCRYPTION_KEY)  # validate
    except Exception as e:
        raise ValueError(f"Invalid FIELD_ENCRYPTION_KEY → {e}")
else:
    if not FIELD_ENCRYPTION_KEY:
        print("WARNING: FIELD_ENCRYPTION_KEY not found – using unencrypted fields locally")

# ========================= ALLAUTH =========================
AUTHENTICATION_BACKENDS = [
    'allauth.account.auth_backends.AuthenticationBackend',  # MUST be first
    'django.contrib.auth.backends.ModelBackend',
]

SITE_ID = 1

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/accounts/login/'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/dashboard/'

LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_LOGOUT_ON_GET = True

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # dev only
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
# ========================= EMAIL CONFIGURATION =========================
if os.getenv('RENDER'):
    # Production: Use SendGrid or SMTP
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDGRID_SANDBOX_MODE_IN_DEBUG = False
else:
    # Local Development: Print emails to terminal console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Shared settings (used by console backend to avoid errors)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'complylaw@alhambra-solutions.com')


#SENDGRID_SANDBOX_MODE_IN_DEBUG =  

EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')  # Bluehost: mail.yourdomain.com
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False') == 'True'  # True for port 587
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True') == 'True'  # True for port 465
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # your full Bluehost email
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # your Bluehost email password
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
EMAIL_TIMEOUT = 10



# ========================= STRIPE Settings =========================
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')
STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO', 'price_...')
STRIPE_PRICE_BASIC = os.getenv('STRIPE_PRICE_BASIC', 'price_...')

# ========================= RATE LIMIT =========================
RATELIMIT_VIEW = 'scanner.views.rate_limit_exceeded_view'
RATELIMIT_VIEW_KWARGS = {
    'template_name': '429.html',
    'status_code': 429,
    'content_type': 'text/html',
}

# ========================= INSTALLED APPS =========================
INSTALLED_APPS = [
    # Django
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',

    # Third-party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_htmx',
    'channels',
    'auditlog',
    'encrypted_model_fields',
    'django_ratelimit',
    

    # Local
    'users',
    'scanner',
    'reports',
    'dashboard',
    'billing',
    'checklists',
]

# ========================= MIDDLEWARE =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# ========================= TEMPLATES =========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "core.context_processors.site_domain",
            ],
        },
    },
]

# ========================= CHANNELS =========================
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

if os.getenv('RENDER'):
    import redis
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis connection successful", file=sys.stderr)
    except Exception as e:
        raise ValueError(f"Redis connection failed: {e}")
        
        
        
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {"hosts": [REDIS_URL]},
    },
}

# ========================= AUTH USER =========================
AUTH_USER_MODEL = 'users.UserAccount'

# ========================= STATIC & MEDIA =========================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========================= CACHES (for django-ratelimit) =========================
if os.getenv('RENDER'):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_URL}/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
            #"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


# ========================= CELERY =========================
#CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
#CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', f"{REDIS_URL}/0")
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', f"{REDIS_URL}/0")

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'



# ========================= DEFAULT AUTO FIELD =========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




# ========================= LOGGING in debug.log FILE =========================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# ========================= DYNAMIC SITE INFO =========================
SITE_NAME = os.getenv("SITE_NAME", "ComplyLaw")
SITE_DOMAIN = os.getenv(
    "SITE_DOMAIN",
    "complylaw-v1.onrender.com" if os.getenv("RENDER") else "localhost:8000"
)
