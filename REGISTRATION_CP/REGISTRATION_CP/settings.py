
from pathlib import Path
import os
from decouple import config
from datetime import timedelta
from utils.log_handlers import GZipRotatingFileHandler


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATIC_URL = 'static/'
FRONTEND_URL = 'http://127.0.0.1:8000/'  

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL='/media/'


SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", cast=bool)


ALLOWED_HOSTS = config("ALLOWED_HOSTS").split(",")


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'simple_history',
    'import_export',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'social_django',  # Add social auth app  
    'corsheaders',
    'users',
    'subscriptions',
    'payments',
   
]


MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'REGISTRATION_CP.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'REGISTRATION_CP.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DATABASE_NAME'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST'),
        'PORT': config('DATABASE_PORT')
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',  
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]


AUTH_USER_MODEL = 'users.User'


# Google OAuth2 settings
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
GOOGLE_OAUTH2_SECRET = config("GOOGLE_OAUTH2_SECRET")
GOOGLE_OAUTH2_REDIRECT_URI = config("GOOGLE_OAUTH2_REDIRECT_URI")
GOOGLE_OAUTH2_SCOPE = ['email', 'profile']


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Berlin'

USE_TZ = True

USE_I18N = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


#CORS settings 
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000", 
   
]

SIMPLE_JWT = {
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


JAZZMIN_SETTINGS = {
    "site_title": "CampusPlatz Admin",
    "site_header": "CampusPlatz Administration",
    "site_brand": "CampusPlatz Admin",
    "welcome_sign": "Welcome to CampusPlatz Admin",
    "copyright": "CampusPlatz", }


JAZZMIN_UI_TWEAKS = {
    "theme": "cyborg", } # Choose from: darkly, cyborg, superhero, slate


STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET")
TUTOR_SUBSCRIPTION_PRICE_ID = config("TUTOR_SUBSCRIPTION_PRICE_ID")
USER_SUBSCRIPTION_PRICE_ID = config("USER_SUBSCRIPTION_PRICE_ID")
PREMIUM_SUCCESS_URL = config("PREMIUM_SUCCESS_URL")
PREMIUM_CANCEL_URL = config("PREMIUM_CANCEL_URL")

#================================================== LOGGING ========================================================================



LOG_DIR = BASE_DIR / 'logs'

log_paths = [
    LOG_DIR / 'users' / 'views',
    LOG_DIR / 'users' / 'models',
    LOG_DIR / 'payments' / 'views',
    LOG_DIR / 'utils' ,
]

for path in log_paths:
    path.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] [{name}] {message}',
            'style': '{',
        },
    },
    
    'handlers': {
        'user_model_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'models' / 'UserModel.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'user_model_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'models' / 'UserModel.error.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'user_manager_model_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'models' / 'UserManagerModel.info.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'user_manager_model_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'models' / 'UserManagerModel.error.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'user_signup_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' /  'UserSignup.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'user_signup_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'UserSignup.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'tutor_signup_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'TutorSignup.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'tutor_signup_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'TutorSignup.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'login_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'Login.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'login_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'Login.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'google_loginsignup_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'GoogleLoginSignup.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'google_loginsignup_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'GoogleLoginSignup.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'tutor_subscription_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'TutorSubscription.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'tutor_subscription_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'TutorSubscription.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'existing_customer_subscription_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'ExistingCustomerPremiumSubscription.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'existing_customer_subscription_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'ExistingCustomerPremiumSubscription.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'email_verification_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'EmailVerification.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'email_verification_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'users' / 'views' / 'EmailVerification.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'stripe_subscription_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'payments' / 'views' / 'StripeSubscriptionPayments.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'stripe_subscription_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'payments' / 'views' / 'StripeSubscriptionPayments.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'handle_sub_for_tutoring_info': {
            'level': 'INFO',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'payments' / 'views' / 'HandleSubscriptionForTutoring.info.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'handle_sub_for_tutoring_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'payments' / 'views' / 'HandleSubscriptionForTutoring.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'uni_email_validator_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'utils' / 'UniEmailValidator.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'datetime_formatting_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'utils' / 'DatetimeFormatting.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'utils_error': {
            'level': 'ERROR',
            'class': GZipRotatingFileHandler,
            'filename': LOG_DIR / 'utils' / 'Utils.error.log',
            'maxBytes': 1024 * 1024 * 5, 
            'backupCount': 7,
            'formatter': 'verbose',
        },




    },  



    'loggers': {
        'users.models.User': {
            'handlers': ['user_model_info', 'user_model_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.models.UserManager': {
            'handlers': ['user_manager_model_info', 'user_manager_model_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.CustomerSignup': {
            'handlers': ['user_signup_info', 'user_signup_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.TutorSignup': {
            'handlers': ['tutor_signup_info', 'tutor_signup_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.Login': {
            'handlers': ['login_info', 'login_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.GoogleLoginSignup': {
            'handlers': ['google_loginsignup_info', 'google_loginsignup_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.ExistingTutorPremiumSubscription': {
            'handlers': ['tutor_subscription_info', 'tutor_subscription_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.ExistingCustomerPremiumSubscription': {
            'handlers': ['existing_customer_subscription_info', 'existing_customer_subscription_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views.EmailVerification': {
            'handlers': ['email_verification_info', 'email_verification_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments.views.StripeSubscriptionWebhook': {
            'handlers': ['stripe_subscription_info', 'stripe_subscription_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments.handle_sub_types.TutoringLogger': {
            'handlers': ['handle_sub_for_tutoring_info', 'handle_sub_for_tutoring_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'UniEmailValidator': {
            'handlers': ['uni_email_validator_error'],
            'level': 'ERROR',
            'propagate': False,
        },
        'DatetimeFormatting': {
            'handlers': ['datetime_formatting_error'],
            'level': 'ERROR',
            'propagate': False,
        },
        'Utils': {
            'handlers': ['utils_error'],
            'level': 'ERROR',
            'propagate': False,
        },




    },  
}

