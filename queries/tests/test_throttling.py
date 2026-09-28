from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from queries.services.throttles import NLQueryBurstThrottle, NLQueryDailyThrottle, NLQueryGlobalThrottle

User = get_user_model()


class NLQueryThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache and would leak between tests
        self.user = User.objects.create_user(email="a@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(email="b@example.com", password="StrongPass123!")
        self.url = reverse("nl-to-sql")  

    @mock.patch.object(NLQueryBurstThrottle, "THROTTLE_RATES", {"nl_query_burst": "2/min"})
    @mock.patch("queries.views.LLMQueryService")
    def test_burst_limit_returns_429(self, mock_llm):
        mock_llm.return_value.generate_sql.return_value = "SELECT 1"
        self.client.force_authenticate(user=self.user)
        for _ in range(2):
            self.client.post(self.url, {"question": "x"})
        response = self.client.post(self.url, {"question": "x"})
        self.assertEqual(response.status_code, 429)

    @mock.patch.object(NLQueryBurstThrottle, "THROTTLE_RATES", {"nl_query_burst": "1/min"})
    @mock.patch("queries.views.LLMQueryService")
    def test_one_users_limit_does_not_affect_another(self, mock_llm):
        mock_llm.return_value.generate_sql.return_value = "SELECT 1"
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, {"question": "x"})
        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.url, {"question": "x"})
        self.assertNotEqual(response.status_code, 429)

    @mock.patch.object(NLQueryGlobalThrottle, "THROTTLE_RATES", {"nl_query_global": "1/day"})
    @mock.patch("queries.views.LLMQueryService")
    def test_global_limit_applies_across_users(self, mock_llm):
        mock_llm.return_value.generate_sql.return_value = "SELECT 1"
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, {"question": "x"})
        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.url, {"question": "x"})
        self.assertEqual(response.status_code, 429)