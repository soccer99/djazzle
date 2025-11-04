from django.conf import settings


def get_psycopg_dsn(alias="default") -> str:
    """
    Build a psycopg DSN from Django DATABASES settings.
    """
    db = settings.DATABASES[alias]
    engine = db.get("ENGINE")
    if "postgresql" not in engine:
        raise ValueError("Djazzle requires a PostgreSQL database")

    user = db.get("USER", "")
    password = db.get("PASSWORD", "")
    host = db.get("HOST", "localhost")
    port = db.get("PORT", 5432)
    name = db.get("NAME")

    dsn = f"dbname={name} user={user} password={password} host={host} port={port}"
    return dsn
