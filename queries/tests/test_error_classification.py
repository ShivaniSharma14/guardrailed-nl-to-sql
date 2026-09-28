from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase

User = get_user_model()


class ErrorClassificationTests(APITestCase):
    """Pins each views.py dispatch branch to the message that triggers it.
    If sql_validator.py or llm_service.py wording changes, these fail loudly
    instead of silently falling through to PIPELINE_EXCEPTION."""

    def setUp(self):
        self.user = User.objects.create_user(email="a@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)
        self.url = reverse("nl-to-sql")  

    def post_with_llm_sql(self, sql):
        with mock.patch("queries.views.LLMQueryService") as llm:
            llm.return_value.generate_sql.return_value = sql
            return self.client.post(self.url, {"question": "anything"})

    def test_multi_statement(self):
        r = self.post_with_llm_sql("SELECT 1; SELECT 2")
        self.assertEqual(r.data["error_code"], "SQL_MULTI_STATEMENT_BLOCKED")

    def test_syntax_error(self):
        # the exact truncated shape from your production bug
        r = self.post_with_llm_sql("SELECT * FROM customers WHERE id =")
        self.assertEqual(r.data["error_code"], "SQL_SYNTAX_INVALID")

    @mock.patch("queries.views.SQLExecutorService")
    def test_result_limit_exceeded(self, mock_exec):
        # unreachable end-to-end since the validator clamps LIMIT, but the
        # dispatch branch itself is still worth pinning (defense in depth)
        mock_exec.return_value.execute_query.side_effect = ValidationError(
            "Database Protection: Result Limit Exceeded"
        )
        r = self.post_with_llm_sql("SELECT * FROM customers")
        self.assertEqual(r.data["error_code"], "RESULT_LIMIT_EXCEEDED")
        self.assertEqual(r.data["error"], "The query results exceeded the maximum allowed rows and was blocked.")

    def test_truncated_response(self):
        with mock.patch("queries.views.LLMQueryService") as llm:
            llm.return_value.generate_sql.side_effect = ValidationError(
                "AI Provider Service Failure: The generated query was cut off before completion"
            )
            r = self.client.post(self.url, {"question": "anything"})
        self.assertEqual(r.data["error_code"], "RESPONSE_TRUNCATED")