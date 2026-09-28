from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from queries.models import QueryLog

User = get_user_model()


class QueryHistoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(email="b@example.com", password="StrongPass123!")
        self.url = reverse("query-history")  # add namespace if your urls use one

    def make_log(self, user, **overrides):
        defaults = dict(
            user=user,
            question="How many orders?",
            ai_proposed_sql="SELECT 1",
            validated_secure_sql="SELECT 1 LIMIT 100",
            status="success",
            row_count=1,
            latency_ms=10,
        )
        defaults.update(overrides)
        return QueryLog.objects.create(**defaults)

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_logs(self):
        mine = self.make_log(self.user)
        self.make_log(self.other)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(str(response.data["results"][0]["id"]), str(mine.id))

    def test_ordered_newest_first(self):
        now = timezone.now()
        old = self.make_log(self.user)
        mid = self.make_log(self.user)
        new = self.make_log(self.user)
        # set timestamps explicitly so the test never depends on clock resolution
        QueryLog.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=2))
        QueryLog.objects.filter(pk=mid.pk).update(created_at=now - timedelta(days=1))
        QueryLog.objects.filter(pk=new.pk).update(created_at=now)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        ids = [str(item["id"]) for item in response.data["results"]]
        self.assertEqual(ids, [str(new.id), str(mid.id), str(old.id)])

    def test_pagination_default_page_size(self):
        for _ in range(25):
            self.make_log(self.user)
        self.client.force_authenticate(user=self.user)

        page1 = self.client.get(self.url)
        page2 = self.client.get(self.url, {"page": 2})

        self.assertEqual(page1.data["count"], 25)
        self.assertEqual(len(page1.data["results"]), 20)
        self.assertEqual(len(page2.data["results"]), 5)

    def test_page_size_is_clamped_to_max(self):
        QueryLog.objects.bulk_create(
            [QueryLog(user=self.user, question="q", status="success") for _ in range(101)]
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {"page_size": 1000})

        self.assertEqual(len(response.data["results"]), 100)

    def test_internal_fields_are_never_exposed(self):
        self.make_log(
            self.user,
            ai_proposed_sql="SELECT secret_llm_output",
            error_message="internal stack detail xyz",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        item = response.data["results"][0]
        self.assertNotIn("ai_proposed_sql", item)
        self.assertNotIn("error_message", item)
        # also guard against the values leaking under any other key
        self.assertNotIn(b"secret_llm_output", response.content)
        self.assertNotIn(b"internal stack detail xyz", response.content)

    def test_blocked_queries_appear_in_history(self):
        self.make_log(
            self.user,
            question="delete all customers",
            status="blocked",
            error_code="VALIDATION_FAILED",  # use one of your real codes
            validated_secure_sql="",         # or None, whichever your model allows
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "blocked")

    def test_orphaned_logs_are_visible_to_nobody(self):
        self.make_log(None)  # simulates a log whose user was deleted (SET_NULL)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 0)

    def test_post_is_not_allowed(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"question": "x"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)