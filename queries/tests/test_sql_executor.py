from django.core.exceptions import ValidationError
from django.test import TestCase

from queries.services.sql_executor import SQLExecutorService


class SQLExecutorValidQueryTests(TestCase):
    def setUp(self):
        self.executor = SQLExecutorService()

    def test_simple_select_returns_expected_row(self):
        results = self.executor.execute_query("SELECT 1 AS num")
        self.assertEqual(results, [{"num": 1}])

    def test_result_is_list_of_dicts_with_correct_columns(self):
        results = self.executor.execute_query("SELECT 1 AS a, 2 AS b")
        self.assertEqual(results, [{"a": 1, "b": 2}])

    def test_multiple_rows_returned_correctly(self):
        results = self.executor.execute_query(
            "SELECT generate_series(1, 5) AS num"
        )
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0], {"num": 1})
        self.assertEqual(results[-1], {"num": 5})

    def test_empty_result_set_returns_empty_list(self):
        results = self.executor.execute_query("SELECT 1 AS num WHERE FALSE")
        self.assertEqual(results, [])


class SQLExecutorRowLimitTests(TestCase):
    def setUp(self):
        self.executor = SQLExecutorService(max_rows=100)

    def test_result_within_limit_succeeds(self):
        results = self.executor.execute_query(
            "SELECT generate_series(1, 100) AS num"
        )
        self.assertEqual(len(results), 100)

    def test_result_exceeding_limit_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.executor.execute_query("SELECT generate_series(1, 150) AS num")

    def test_custom_max_rows_is_respected(self):
        strict_executor = SQLExecutorService(max_rows=5)
        with self.assertRaises(ValidationError):
            strict_executor.execute_query("SELECT generate_series(1, 10) AS num")

    def test_row_limit_error_is_currently_reported_as_runtime_exception(self):
        """
        Previously this ValidationError was caught by the surrounding
        except-block and re-wrapped as a generic 'Database Runtime
        Exception', misclassifying a guardrail event as a DB failure.
        Fixed: the row-limit check now raises outside the try/except.
        """
        with self.assertRaises(ValidationError) as ctx:
            self.executor.execute_query("SELECT generate_series(1, 150) AS num")
        self.assertIn("Result Limit Exceeded", str(ctx.exception))
        self.assertNotIn("Database Runtime Exception", str(ctx.exception))


class SQLExecutorDatabaseErrorTests(TestCase):
    def setUp(self):
        self.executor = SQLExecutorService()

    def test_query_against_nonexistent_table_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self.executor.execute_query("SELECT * FROM this_table_does_not_exist_xyz")
        self.assertIn("Database Runtime Exception", str(ctx.exception))

    def test_executor_recovers_after_a_failed_query(self):
        # Proves one bad query doesn't leave the connection/transaction
        # in a broken state for the next call — important since each
        # execute_query wraps itself in its own transaction.atomic().
        with self.assertRaises(ValidationError):
            self.executor.execute_query("SELECT * FROM this_table_does_not_exist_xyz")

        results = self.executor.execute_query("SELECT 1 AS num")
        self.assertEqual(results, [{"num": 1}])


class SQLExecutorTimeoutTests(TestCase):
    def test_query_exceeding_statement_timeout_raises_validation_error(self):
        fast_timeout_executor = SQLExecutorService(timeout_ms=100)
        with self.assertRaises(ValidationError) as ctx:
            fast_timeout_executor.execute_query("SELECT pg_sleep(1)")
        self.assertIn("Database Runtime Exception", str(ctx.exception))