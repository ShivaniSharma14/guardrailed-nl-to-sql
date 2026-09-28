from django.test import TestCase

from queries.services.schema_discovery import SchemaDiscoveryService


class SchemaDiscoveryServiceTests(TestCase):
    def setUp(self):
        self.service = SchemaDiscoveryService()

    def test_discovers_expected_target_tables(self):
        result = self.service.discover_schema()
        for table in ("customers", "products", "orders", "order_items"):
            self.assertIn(f"TABLE {table}", result)

    def test_output_includes_column_names_and_types(self):
        result = self.service.discover_schema()
        # We don't hardcode every column here — that would make this test
        # brittle against any future schema change. We just prove the
        # format contract holds: at least one "- name (TYPE)" line exists.
        self.assertRegex(result, r"- \w+ \(\w+\)")

    def test_output_starts_with_header(self):
        result = self.service.discover_schema()
        self.assertTrue(result.startswith("Available Database Schema:"))

    def test_does_not_include_unrelated_django_tables(self):
        result = self.service.discover_schema()
        # auth/session/admin tables must never leak into the LLM's context —
        # this is a real information-boundary check, not decoration
        self.assertNotIn("auth_user", result.lower())
        self.assertNotIn("django_session", result.lower())
        self.assertNotIn("query_logs", result.lower())