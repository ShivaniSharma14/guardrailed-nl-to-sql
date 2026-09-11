from django.core.exceptions import ValidationError
from django.db import connection


class SQLExecutorService:
    def __init__(self, timeout_ms: int = 2000, max_rows: int = 100):
        self.timeout_ms = timeout_ms
        self.max_rows = max_rows

    def execute_query(self, secure_sql: str) -> list[dict]:
        """
        Executes a secure SQL string against PostgreSQL.
        Enforces local statement timeouts and caps maximum memory rows.
        """
        with connection.cursor() as cursor:
            try:
                # Enforce a local timeout ONLY for this single query call
                cursor.execute(f"SET LOCAL statement_timeout = {self.timeout_ms};")

                # Execute the safe SQLGlot-verified query
                cursor.execute(secure_sql)

                # Canary check: fetch up to max_rows + 1 to detect overflow
                rows = cursor.fetchmany(self.max_rows + 1)

                if len(rows) > self.max_rows:
                    raise ValidationError(
                        f"Database Protection: Query results exceeded the safe threshold of {self.max_rows} rows."
                    )

                if not cursor.description:
                    return []

                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

            except Exception as e:
                raise ValidationError(
                    f"Database Runtime Exception: The query failed during execution. Details: {e}"
                )
