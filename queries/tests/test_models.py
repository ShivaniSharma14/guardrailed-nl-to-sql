from django.contrib.auth import get_user_model
from django.test import TestCase

from queries.models import QueryLog

User = get_user_model()


class QueryLogModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="loguser@example.com", password="StrongPass123!"
        )

    def test_default_status_is_processing(self):
        log = QueryLog.objects.create(user=self.user, question="Show revenue")
        self.assertEqual(log.status, "processing")

    def test_default_row_count_and_latency_are_zero(self):
        log = QueryLog.objects.create(user=self.user, question="Show revenue")
        self.assertEqual(log.row_count, 0)
        self.assertEqual(log.latency_ms, 0)

    def test_optional_fields_can_be_blank(self):
        log = QueryLog.objects.create(user=self.user, question="Show revenue")
        self.assertIsNone(log.ai_proposed_sql)
        self.assertIsNone(log.validated_secure_sql)
        self.assertIsNone(log.error_code)
        self.assertIsNone(log.error_message)

    def test_created_at_is_set_automatically(self):
        log = QueryLog.objects.create(user=self.user, question="Show revenue")
        self.assertIsNotNone(log.created_at)

    def test_str_representation_includes_key_fields(self):
        log = QueryLog.objects.create(
            user=self.user, question="Show revenue", status="success", latency_ms=42
        )
        text = str(log)
        self.assertIn(str(log.id), text)
        self.assertIn("loguser@example.com", text)
        self.assertIn("success", text)
        self.assertIn("42ms", text)

    def test_deleting_user_cascades_to_query_logs(self):
        log = QueryLog.objects.create(user=self.user, question="Show revenue")
        log_id = log.id
        self.user.delete()
        self.assertFalse(QueryLog.objects.filter(id=log_id).exists())

    def test_ordering_is_most_recent_first(self):
        first = QueryLog.objects.create(user=self.user, question="First")
        second = QueryLog.objects.create(user=self.user, question="Second")
        logs = list(QueryLog.objects.all())
        self.assertEqual(logs[0], second)
        self.assertEqual(logs[1], first)

    def test_user_can_have_multiple_query_logs(self):
        QueryLog.objects.create(user=self.user, question="Q1")
        QueryLog.objects.create(user=self.user, question="Q2")
        self.assertEqual(self.user.query_logs.count(), 2)