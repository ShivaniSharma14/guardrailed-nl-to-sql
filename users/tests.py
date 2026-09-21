from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from users.serializers import UserRegisterSerializer

User = get_user_model()


class CustomUserManagerTests(TestCase):
    """
    Unit tests for CustomUserManager — no HTTP involved.
    If something breaks here, it breaks everywhere built on top of it,
    so this is the fastest and most isolated layer to test first.
    """

    def test_create_user_with_email_succeeds(self):
        user = User.objects.create_user(email="alice@example.com", password="StrongPass123!")
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed_not_stored_plain(self):
        user = User.objects.create_user(email="bob@example.com", password="StrongPass123!")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="StrongPass123!")

    def test_email_domain_is_normalized(self):
        user = User.objects.create_user(email="carl@EXAMPLE.com", password="StrongPass123!")
        self.assertEqual(user.email, "carl@example.com")

    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(email="dupe@example.com", password="StrongPass123!")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dupe@example.com", password="AnotherPass123!")

    def test_create_superuser_sets_flags(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="StrongPass123!")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com", password="StrongPass123!", is_staff=False
            )

    def test_str_returns_email(self):
        user = User.objects.create_user(email="dana@example.com", password="StrongPass123!")
        self.assertEqual(str(user), "dana@example.com")


class UserRegisterSerializerTests(TestCase):
    """
    Unit tests for the serializer, bypassing HTTP entirely.
    """

    def test_valid_data_is_valid(self):
        serializer = UserRegisterSerializer(
            data={"email": "ser@example.com", "password": "StrongPass123!"}
        )
        self.assertTrue(serializer.is_valid())

    def test_weak_numeric_password_is_invalid(self):
        serializer = UserRegisterSerializer(
            data={"email": "ser2@example.com", "password": "12345678"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_excluded_from_serialized_output(self):
        serializer = UserRegisterSerializer(
            data={"email": "ser3@example.com", "password": "StrongPass123!"}
        )
        serializer.is_valid()
        serializer.save()
        self.assertNotIn("password", serializer.data)


class UserRegisterAPITests(APITestCase):
    url = "/api/auth/register/"

    def test_register_with_valid_data_creates_user(self):
        payload = {"email": "newuser@example.com", "password": "StrongPass123!"}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
        self.assertNotIn("password", response.data.get("user", {}))

    def test_password_is_hashed_in_database(self):
        payload = {"email": "hashcheck@example.com", "password": "StrongPass123!"}
        self.client.post(self.url, payload, format="json")

        user = User.objects.get(email="hashcheck@example.com")
        self.assertNotEqual(user.password, "StrongPass123!")

    def test_register_missing_email_returns_400(self):
        response = self.client.post(self.url, {"password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password_returns_400(self):
        response = self.client.post(self.url, {"email": "nopass@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_returns_400(self):
        response = self.client.post(
            self.url, {"email": "weak@example.com", "password": "12345678"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())

    def test_register_duplicate_email_returns_400(self):
        User.objects.create_user(email="exists@example.com", password="StrongPass123!")
        response = self.client.post(
            self.url,
            {"email": "exists@example.com", "password": "AnotherPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITests(APITestCase):
    url = "/api/auth/login/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="loginuser@example.com", password="StrongPass123!"
        )

    def test_login_with_valid_credentials_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"email": "loginuser@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "loginuser@example.com")

    def test_access_token_contains_correct_user_id(self):
        response = self.client.post(
            self.url,
            {"email": "loginuser@example.com", "password": "StrongPass123!"},
            format="json",
        )
        access = AccessToken(response.data["access"])
        self.assertEqual(str(access["user_email"]), str(self.user.email))


    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post(
            self.url, {"email": "loginuser@example.com", "password": "WrongPass!"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_nonexistent_email_returns_401(self):
        response = self.client.post(
            self.url, {"email": "ghost@example.com", "password": "StrongPass123!"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_password_returns_400(self):
        response = self.client.post(self.url, {"email": "loginuser@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_email_returns_400(self):
        response = self.client.post(self.url, {"password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRefreshAPITests(APITestCase):
    url = "/api/auth/refresh/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="refreshuser@example.com", password="StrongPass123!"
        )

    def test_valid_refresh_token_returns_new_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token_returns_401(self):
        response = self.client.post(self.url, {"refresh": "not-a-real-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
