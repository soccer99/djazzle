import os

SECRET_KEY = "fake-key-for-tests"
INSTALLED_APPS = [
    "tests.apps.TestsConfig",   # include your tests package as a Django app
    "django.contrib.contenttypes",  # required for models
    "django.contrib.auth",
]

# Use PostgreSQL if environment variables are set, otherwise use SQLite
if os.environ.get("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "testdb"),
            "USER": os.environ.get("DB_USER", "test"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "test"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = False
