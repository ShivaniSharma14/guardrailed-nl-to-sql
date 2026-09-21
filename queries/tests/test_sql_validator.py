from django.core.exceptions import ValidationError
from django.test import TestCase

from queries.services.sql_validator import SQLValidatorService


class SQLValidatorAcceptsSafeQueriesTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_simple_select_is_accepted(self):
        sql = self.validator.validate_query("SELECT * FROM customers")
        self.assertIn("SELECT", sql.upper())

    def test_select_with_join_is_accepted(self):
        sql = "SELECT c.region, o.revenue FROM orders o JOIN customers c ON o.customer_id = c.id"
        result = self.validator.validate_query(sql)
        self.assertIn("JOIN", result.upper())

    def test_select_with_group_by_is_accepted(self):
        sql = "SELECT region, COUNT(*) FROM customers GROUP BY region"
        result = self.validator.validate_query(sql)
        self.assertIn("GROUP BY", result.upper())

    def test_cte_referencing_allowed_table_is_accepted(self):
        sql = (
            "WITH regional AS (SELECT region FROM customers) "
            "SELECT * FROM regional"
        )
        # Must not be rejected just because 'regional' isn't a real table
        result = self.validator.validate_query(sql)
        self.assertIn("SELECT", result.upper())


class SQLValidatorRejectsWriteOperationsTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_delete_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("DELETE FROM customers")

    def test_update_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("UPDATE customers SET region = 'North'")

    def test_insert_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("INSERT INTO customers (region) VALUES ('North')")

    def test_drop_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("DROP TABLE customers")

    def test_alter_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("ALTER TABLE customers ADD COLUMN foo TEXT")

    def test_truncate_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("TRUNCATE customers")


class SQLValidatorRejectsStackedStatementsTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_select_followed_by_drop_is_rejected(self):
        sql = "SELECT * FROM customers; DROP TABLE customers;"
        with self.assertRaises(ValidationError):
            self.validator.validate_query(sql)

    def test_two_select_statements_is_rejected(self):
        sql = "SELECT * FROM customers; SELECT * FROM products;"
        with self.assertRaises(ValidationError):
            self.validator.validate_query(sql)


class SQLValidatorRejectsUnauthorizedTablesTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_unknown_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("SELECT * FROM secret_table")

    def test_unauthorized_table_in_join_is_rejected(self):
        sql = "SELECT * FROM customers JOIN users ON customers.id = users.customer_id"
        with self.assertRaises(ValidationError):
            self.validator.validate_query(sql)

    def test_cte_alias_is_not_mistaken_for_real_table(self):
        # 'filtered' is a CTE name, not a physical table — must NOT trigger the allowlist check
        sql = "WITH filtered AS (SELECT * FROM customers) SELECT * FROM filtered"
        result = self.validator.validate_query(sql)
        self.assertIsNotNone(result)

    def test_cte_body_referencing_unauthorized_table_is_still_rejected(self):
        # The CTE alias is allowed, but its inner query hits a disallowed table
        sql = "WITH leaky AS (SELECT * FROM secret_table) SELECT * FROM leaky"
        with self.assertRaises(ValidationError):
            self.validator.validate_query(sql)

    def test_custom_allowlist_restricts_further(self):
        strict_validator = SQLValidatorService(allowed_tables=["customers"])
        with self.assertRaises(ValidationError):
            strict_validator.validate_query("SELECT * FROM products")

    def test_custom_allowlist_permits_configured_table(self):
        strict_validator = SQLValidatorService(allowed_tables=["customers"])
        result = strict_validator.validate_query("SELECT * FROM customers")
        self.assertIsNotNone(result)

    def test_table_name_check_is_case_insensitive(self):
        result = self.validator.validate_query("SELECT * FROM CUSTOMERS")
        self.assertIsNotNone(result)


class SQLValidatorSyntaxErrorTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_malformed_sql_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("SELECT * FROM customers WHERE (")

    def test_empty_string_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_query("")


class SQLValidatorLimitInjectionTests(TestCase):
    def setUp(self):
        self.validator = SQLValidatorService()

    def test_query_without_limit_gets_limit_100_injected(self):
        result = self.validator.validate_query("SELECT * FROM customers")
        self.assertIn("LIMIT 100", result.upper())

    def test_query_with_existing_smaller_limit_is_preserved(self):
        result = self.validator.validate_query("SELECT * FROM customers LIMIT 10")
        self.assertIn("LIMIT 10", result.upper())
        self.assertNotIn("LIMIT 100", result.upper())

    def test_subquery_without_limit_also_gets_limit_injected(self):
        sql = (
            "SELECT * FROM (SELECT * FROM customers) AS sub"
        )
        result = self.validator.validate_query(sql)
        # both the outer query and the inner subquery should be bounded
        self.assertEqual(result.upper().count("LIMIT 100"), 2)


class SQLValidatorUnionBehaviorTests(TestCase):
    """
    Documents actual current behavior for UNION queries — not necessarily
    desired behavior. A top-level UNION parses to exp.Union, not exp.Select,
    so it currently gets rejected by Guardrail 2, mislabeled as a
    'write operation'. This test locks in that this is what happens today,
    so a future change to this behavior is a deliberate decision, not an
    accidental regression.
    """

    def setUp(self):
        self.validator = SQLValidatorService()

    def test_union_of_two_selects_is_currently_rejected(self):
        sql = "SELECT region FROM customers UNION SELECT region FROM customers"
        with self.assertRaises(ValidationError):
            self.validator.validate_query(sql)