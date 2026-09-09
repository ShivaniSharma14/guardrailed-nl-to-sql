import sqlglot
from sqlglot import exp
from django.core.exceptions import ValidationError

class SQLValidatorService:
    """
    The main security boundary of our application. It parses untrusted LLM-generated SQL
    into an Abstract Syntax Tree (AST) and enforces strict enterprise guardrails.
    """

    def __init__(self, allowed_tables=None):
        # Whitelist of tables the AI is physically authorized to read
        self.allowed_tables = {t.lower() for t in (allowed_tables or ["customers", "products", "orders", "order_items"])}

    def validate_query(self, raw_sql: str) -> str:
        """
        Parses and validates a raw SQL string.
        Returns a clean, safety-injected SQL string if safe, or raises a ValidationError.
        """
        try:
            # 1. Parse the SQL string specifically using the PostgreSQL dialect.
            expressions = sqlglot.parse(raw_sql, read="postgres")
        except sqlglot.errors.ParseError as e:
            raise ValidationError(f"SQL Syntax Error: The query could not be parsed. Details: {e}")

        # Guardrail 1: Enforce exactly ONE statement to block stacked injection attacks
        if len(expressions) != 1 or not expressions[0]:
            raise ValidationError("Security Violation: Multiple or invalid SQL statements detected.")

        ast = expressions[0]

        # Guardrail 2: Enforce Read-Only Operations. ONLY allow SELECT queries.
        if not isinstance(ast, exp.Select):
            raise ValidationError(f"Security Violation: Prohibited database write operation attempted ({type(ast).__name__}).")

        # Extract CTE names so we don't accidentally treat them as real database tables
        cte_names = {cte.alias.lower() for cte in ast.find_all(exp.CTE) if cte.alias}

        # Guardrail 3: Table Allowlist Check (Scan the entire AST tree for physical table nodes)
        for table_expr in ast.find_all(exp.Table):
            table_name = table_expr.name.lower()
            
            # If the table reference is just a local CTE alias, bypass the allowlist check
            if table_name in cte_names:
                continue
                
            if table_name not in self.allowed_tables:
                raise ValidationError(f"Security Violation: Unauthorized table access attempted: '{table_name}'.")

        # Guardrail 4: Performance Protection - Forcefully inject a maximum LIMIT clause on all Select components.
        if isinstance(ast, exp.Select) and not ast.args.get("limit"):
            ast = ast.limit(100)
            
        for sub_select in ast.find_all(exp.Select):
            if not sub_select.args.get("limit"):
                sub_select.set("limit", exp.Limit(expression=exp.Literal.number(100)))

        # Return the verified, clean, compiled SQL string back to the request loop
        return ast.sql(dialect="postgres")

