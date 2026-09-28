import os
from unittest import mock

from openai import RateLimitError

from django.core.exceptions import ValidationError
from django.test import TestCase

from queries.services.llm_service import LLMQueryService

def _mock_completion(content: str, finish_reason: str = "stop"):
    """Builds a fake OpenAI response shaped like response.choices[0].message.content"""
    mock_message = mock.Mock()
    mock_message.content = content
    mock_choice = mock.Mock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = finish_reason
    mock_response = mock.Mock()
    mock_response.choices = [mock_choice]
    return mock_response


@mock.patch.dict(os.environ, {"AI_PROVIDER_API_KEY": "fake-key-for-tests"})
class LLMQueryServiceInitTests(TestCase):
    def test_missing_api_key_raises_validation_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                LLMQueryService()

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_initializes_with_default_base_url_and_model(self, mock_openai_class):
        service = LLMQueryService()
        self.assertEqual(service.base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(service.model_name, "openai/gpt-oss-120b")


@mock.patch.dict(os.environ, {"AI_PROVIDER_API_KEY": "fake-key-for-tests"})
class LLMQueryServiceGenerateSQLTests(TestCase):
    @mock.patch("queries.services.llm_service.OpenAI")
    def test_returns_clean_sql_string(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT * FROM customers"
        )

        service = LLMQueryService()
        result = service.generate_sql("show all customers", "TABLE customers: ...")

        self.assertEqual(result, "SELECT * FROM customers")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_strips_markdown_code_fences(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "```sql\nSELECT * FROM customers\n```"
        )

        service = LLMQueryService()
        result = service.generate_sql("show all customers", "TABLE customers: ...")

        self.assertEqual(result, "SELECT * FROM customers")
        self.assertNotIn("```", result)

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_provider_exception_raises_validation_error(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.side_effect = Exception("connection timed out")

        service = LLMQueryService()
        with self.assertRaises(ValidationError):
            service.generate_sql("show all customers", "TABLE customers: ...")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_temperature_and_model_are_passed_to_provider(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT * FROM customers"
        )

        service = LLMQueryService()
        service.generate_sql("show all customers", "TABLE customers: ...")

        _, call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs["temperature"], 0.0)
        self.assertEqual(call_kwargs["model"], "openai/gpt-oss-120b")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_schema_context_is_included_in_system_prompt(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT * FROM customers"
        )

        service = LLMQueryService()
        service.generate_sql("show all customers", "TABLE customers: (id, region)")

        _, call_kwargs = mock_client.chat.completions.create.call_args
        system_message = call_kwargs["messages"][0]["content"]
        self.assertIn("TABLE customers: (id, region)", system_message)

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_user_question_is_included_in_user_message(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT * FROM customers"
        )

        service = LLMQueryService()
        service.generate_sql("show all customers by region", "TABLE customers: ...")

        _, call_kwargs = mock_client.chat.completions.create.call_args
        user_message = call_kwargs["messages"][1]["content"]
        self.assertIn("show all customers by region", user_message)

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_truncated_completion_raises_validation_error(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        # the exact shape of the production bug: SQL cut off mid-statement
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT SUM(oi.quantity * oi.unit_price) FROM order_items oi "
            "JOIN orders o ON oi.order_id = o.id JOIN customers c ON o.customer_id =",
            finish_reason="length",
        )

        service = LLMQueryService()
        with self.assertRaisesMessage(ValidationError, "cut off before completion"):
            service.generate_sql("revenue by region", "TABLE customers: ...")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_refusal_sentinel_raises_write_violation(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "REFUSED_NON_SELECT_INTENT"
        )

        service = LLMQueryService()
        with self.assertRaisesMessage(
            ValidationError, "Prohibited database write operation"
        ):
            service.generate_sql("delete all customers", "TABLE customers: ...")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_refusal_sentinel_with_whitespace_still_detected(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "  REFUSED_NON_SELECT_INTENT\n"
        )

        service = LLMQueryService()
        with self.assertRaises(ValidationError):
            service.generate_sql("drop everything", "TABLE customers: ...")

    @mock.patch("queries.services.llm_service.OpenAI")
    def test_max_tokens_leaves_headroom_for_join_queries(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = _mock_completion(
            "SELECT * FROM customers"
        )

        service = LLMQueryService()
        service.generate_sql("show all customers", "TABLE customers: ...")

        _, call_kwargs = mock_client.chat.completions.create.call_args
        # regression: 300 silently truncated 3-table join+aggregate queries
        self.assertGreaterEqual(call_kwargs["max_tokens"], 800)



    def test_provider_rate_limit_raises_specific_error(self):
        fake_response = mock.Mock(status_code=429, headers={})
        err = RateLimitError("quota", response=fake_response, body=None)

        with mock.patch.dict("os.environ", {"AI_PROVIDER_API_KEY": "test-key"}):
           service = LLMQueryService()
        service.client = mock.Mock()
        service.client.chat.completions.create.side_effect = err

        with self.assertRaises(ValidationError) as ctx:
            service.generate_sql("q", "schema")

        self.assertIn("AI Provider Rate Limit", str(ctx.exception))