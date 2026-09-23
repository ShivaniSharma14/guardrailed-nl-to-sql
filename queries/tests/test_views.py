from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from queries.models import QueryLog

User = get_user_model()


class NaturalLanguageQueryAuthTests(APITestCase):
    url = "/api/query/"

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(self.url, {"question": "Show revenue"}, format="json")
        self.assertIn(
            response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_unauthenticated_request_creates_no_query_log(self):
        self.client.post(self.url, {"question": "Show revenue"}, format="json")
        self.assertEqual(QueryLog.objects.count(), 0)


class NaturalLanguageQueryValidationTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user = User.objects.create_user(email="qview@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)

    @mock.patch("queries.views.LLMQueryService")
    def test_missing_question_returns_400_and_llm_never_called(self, mock_llm_class):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_llm_class.assert_not_called()

    @mock.patch("queries.views.LLMQueryService")
    def test_invalid_request_creates_no_query_log(self, mock_llm_class):
        self.client.post(self.url, {"question": ""}, format="json")
        self.assertEqual(QueryLog.objects.count(), 0)


class NaturalLanguageQuerySuccessTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user = User.objects.create_user(email="success@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)

    @mock.patch("queries.views.LLMQueryService")
    def test_valid_question_returns_200_with_data(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT 1 AS num"

        response = self.client.post(self.url, {"question": "Show a number"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["data"], [{"num": 1}])

    @mock.patch("queries.views.LLMQueryService")
    def test_successful_query_creates_success_log_with_correct_fields(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT 1 AS num"

        self.client.post(self.url, {"question": "Show a number"}, format="json")

        log = QueryLog.objects.get(user=self.user)
        self.assertEqual(log.status, "success")
        self.assertEqual(log.question, "Show a number")
        self.assertEqual(log.ai_proposed_sql, "SELECT 1 AS num")
        self.assertIn("LIMIT", log.validated_secure_sql.upper())
        self.assertEqual(log.row_count, 1)
        self.assertGreaterEqual(log.latency_ms, 0)

    @mock.patch("queries.views.LLMQueryService")
    def test_response_includes_ai_and_validated_sql_separately(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT 1 AS num"

        response = self.client.post(self.url, {"question": "Show a number"}, format="json")

        self.assertEqual(response.data["ai_proposed_sql"], "SELECT 1 AS num")
        self.assertIn("LIMIT", response.data["validated_secure_sql"].upper())


class NaturalLanguageQueryBlockedSQLTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user = User.objects.create_user(email="blocked@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)

    @mock.patch("queries.views.LLMQueryService")
    def test_llm_proposing_destructive_sql_returns_400(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "DROP TABLE customers"

        response = self.client.post(self.url, {"question": "Delete everything"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "SQL_GUARDRAIL_VIOLATION")

    @mock.patch("queries.views.LLMQueryService")
    def test_blocked_sql_is_recorded_in_log_with_ai_sql_preserved(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "DROP TABLE customers"

        self.client.post(self.url, {"question": "Delete everything"}, format="json")

        log = QueryLog.objects.get(user=self.user)
        self.assertEqual(log.status, "blocked")
        self.assertEqual(log.error_code, "SQL_GUARDRAIL_VIOLATION")
        # The dangerous SQL the AI proposed should still be preserved for audit,
        # even though it was never executed
        self.assertEqual(log.ai_proposed_sql, "DROP TABLE customers")
        self.assertIsNone(log.validated_secure_sql)

    @mock.patch("queries.views.LLMQueryService")
    def test_blocked_sql_never_reaches_database(self, mock_llm_class):
        # This is the architectural invariant that matters most: a rejected
        # query must never touch PostgreSQL at all. We prove it by patching
        # the executor and asserting it's simply never called.
        mock_llm_class.return_value.generate_sql.return_value = "DROP TABLE customers"

        with mock.patch("queries.views.SQLExecutorService") as mock_executor_class:
            self.client.post(self.url, {"question": "Delete everything"}, format="json")
            mock_executor_class.return_value.execute_query.assert_not_called()

    @mock.patch("queries.views.LLMQueryService")
    def test_llm_proposing_unauthorized_table_is_blocked(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT * FROM secret_table"

        response = self.client.post(self.url, {"question": "Show secrets"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "SQL_GUARDRAIL_VIOLATION")


class NaturalLanguageQueryLLMFailureTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user = User.objects.create_user(email="llmfail@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)

    @mock.patch("queries.views.LLMQueryService")
    def test_llm_provider_failure_returns_400_with_pipeline_error_code(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.side_effect = ValidationError(
            "AI Provider Service Failure: Unable to generate query. Details: timeout"
        )

        response = self.client.post(self.url, {"question": "Show revenue"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "PIPELINE_EXCEPTION")

    @mock.patch("queries.views.LLMQueryService")
    def test_llm_failure_is_recorded_as_failed_with_no_proposed_sql(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.side_effect = ValidationError(
            "AI Provider Service Failure: timeout"
        )

        self.client.post(self.url, {"question": "Show revenue"}, format="json")

        log = QueryLog.objects.get(user=self.user)
        self.assertEqual(log.status, "failed")
        self.assertIsNone(log.ai_proposed_sql)


class NaturalLanguageQueryDatabaseFailureTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user = User.objects.create_user(email="dbfail@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)

    @mock.patch("queries.views.SQLExecutorService")
    @mock.patch("queries.views.LLMQueryService")
    def test_execution_failure_returns_database_execution_error_code(
        self, mock_llm_class, mock_executor_class
    ):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT * FROM customers"
        mock_executor_class.return_value.execute_query.side_effect = ValidationError(
            "Database Runtime Exception: connection reset"
        )

        response = self.client.post(self.url, {"question": "Show customers"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "DATABASE_EXECUTION_ERROR")

    @mock.patch("queries.views.SQLExecutorService")
    @mock.patch("queries.views.LLMQueryService")
    def test_execution_failure_still_records_validated_sql_in_log(
        self, mock_llm_class, mock_executor_class
    ):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT * FROM customers"
        mock_executor_class.return_value.execute_query.side_effect = ValidationError(
            "Database Runtime Exception: connection reset"
        )

        self.client.post(self.url, {"question": "Show customers"}, format="json")

        log = QueryLog.objects.get(user=self.user)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.error_code, "DATABASE_EXECUTION_ERROR")
        self.assertIsNotNone(log.validated_secure_sql)


class QueryLogUserIsolationTests(APITestCase):
    url = "/api/query/"

    def setUp(self):
        self.user_a = User.objects.create_user(email="usera@example.com", password="StrongPass123!")
        self.user_b = User.objects.create_user(email="userb@example.com", password="StrongPass123!")

    @mock.patch("queries.views.LLMQueryService")
    def test_query_log_is_attributed_to_the_authenticated_user(self, mock_llm_class):
        mock_llm_class.return_value.generate_sql.return_value = "SELECT 1 AS num"

        self.client.force_authenticate(user=self.user_a)
        self.client.post(self.url, {"question": "Show a number"}, format="json")

        log = QueryLog.objects.get()
        self.assertEqual(log.user, self.user_a)
        self.assertNotEqual(log.user, self.user_b)

# NOTE: A dedicated view-level test for RESULT_LIMIT_EXCEEDED was removed.
# Once SQLValidatorService clamps every LIMIT to MAX_ROW_LIMIT (see
# sql_validator.py), SQLExecutorService can never receive more rows than
# its own max_rows guard allows via the normal pipeline. The executor's
# row-limit guard is still tested directly and independently in
# test_sql_executor.py — it remains a real defense-in-depth layer even
# though the validator should never let it get exercised in practice.