SECRET_KEY = "fake-key-for-tests"
INSTALLED_APPS = [
    "tests",  # include your tests package as a Django app
    "django.contrib.contenttypes",  # required for models
    "django.contrib.auth",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
