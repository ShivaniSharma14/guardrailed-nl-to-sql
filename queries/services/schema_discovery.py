from django.db import connection


class SchemaDiscoveryService:
    """
    A dynamic Runtime Schema Discovery Engine.
    It inspects the live database catalogs at runtime to build
    a clean structural context string for the LLM prompt.
    """

    def discover_schema(self) -> str:
        # Step 1: Query PostgreSQL to find only our target analytical tables
        # This keeps our context focused and clean for the LLM
        table_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('customers', 'products', 'orders', 'order_items');
        """

        with connection.cursor() as cursor:
            cursor.execute(table_query)
            discovered_tables = [row[0] for row in cursor.fetchall()]

        if not discovered_tables:
            return "Available Database Schema: [No target analytics tables found]"

        # Step 2: Dynamically query columns and types for these tables
        column_query = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = ANY(%s)
            ORDER BY table_name, ordinal_position;
        """

        with connection.cursor() as cursor:
            cursor.execute(column_query, [discovered_tables])
            rows = cursor.fetchall()

        # Step 3: Parse the database metadata into a clean mapping dictionary
        schema_map = {}
        for table_name, column_name, data_type in rows:
            if table_name not in schema_map:
                schema_map[table_name] = []
            schema_map[table_name].append((column_name, data_type.upper()))

        return self._format_as_prompt_context(schema_map)

    def _format_as_prompt_context(self, schema_map: dict) -> str:
        """
        Converts the schema map into a clean text block optimized for LLM comprehension.
        """
        context_lines = ["Available Database Schema:"]
        for table_name, columns in schema_map.items():
            context_lines.append(f"\nTABLE {table_name}:")
            for col_name, col_type in columns:
                context_lines.append(f"  - {col_name} ({col_type})")
        return "\n".join(context_lines)
