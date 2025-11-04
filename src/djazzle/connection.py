"""Database connection adapter for supporting multiple connection types."""

from typing import Any, Optional


class ConnectionAdapter:
    """
    Adapter to normalize different database connection types.

    Supports:
    - Django connections (default)
    - psycopg2 (PostgreSQL - sync only)
    - psycopg3 (PostgreSQL - sync and async)
    - mysqlclient (MySQL - sync only)
    - pymysql (MySQL - sync only)
    - aiomysql (MySQL - async only)
    - asyncmy (MySQL - async only)
    """

    def __init__(self, conn):
        self.conn = conn
        self.conn_type = self._detect_connection_type()
        self.is_async = self._is_async_connection()

    def _detect_connection_type(self) -> str:
        """Detect the type of connection."""
        conn_module = type(self.conn).__module__
        conn_class = type(self.conn).__name__

        # Django connection
        if hasattr(self.conn, 'vendor') and hasattr(self.conn, 'alias'):
            return 'django'

        # psycopg2 (sync only) or psycopg3 (sync and async)
        if 'psycopg' in conn_module:
            # Distinguish between psycopg2 and psycopg3
            if 'psycopg2' in conn_module:
                return 'psycopg2'
            elif 'psycopg' in conn_module:
                # psycopg3 - check if it's an async connection
                # AsyncConnection class is in psycopg for v3
                if 'AsyncConnection' in conn_class or hasattr(self.conn, 'execute'):
                    # Check if connection has async methods
                    if hasattr(self.conn, '__aenter__'):
                        return 'psycopg3_async'
                return 'psycopg3'

        # mysqlclient (MySQLdb)
        if 'MySQLdb' in conn_module or '_mysql' in conn_module:
            return 'mysqlclient'

        # pymysql
        if 'pymysql' in conn_module:
            return 'pymysql'

        # aiomysql
        if 'aiomysql' in conn_module:
            return 'aiomysql'

        # asyncmy
        if 'asyncmy' in conn_module:
            return 'asyncmy'

        # Default to django if we can't detect
        return 'django'

    def _is_async_connection(self) -> bool:
        """Check if this is an async connection."""
        return self.conn_type in ('psycopg3_async', 'aiomysql', 'asyncmy')

    def get_db_alias(self) -> str:
        """Get database alias (for Django model instantiation)."""
        if self.conn_type == 'django':
            return self.conn.alias
        # For non-Django connections, use 'default' as alias
        return 'default'

    def cursor(self):
        """Get a cursor from the connection (sync)."""
        if self.is_async:
            raise RuntimeError(
                f"Cannot use sync cursor() with async connection type '{self.conn_type}'. "
                f"Use async methods instead."
            )
        return self.conn.cursor()

    async def async_cursor(self):
        """Get a cursor from the connection (async)."""
        if not self.is_async:
            raise RuntimeError(
                f"Cannot use async_cursor() with sync connection type '{self.conn_type}'. "
                f"Use sync methods instead."
            )
        # aiomysql and asyncmy use async context managers for cursors
        return self.conn.cursor()
