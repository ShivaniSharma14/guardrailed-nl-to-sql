from django.test import TestCase

from queries.serializers import QueryRequestSerializer


class QueryRequestSerializerTests(TestCase):
    def test_valid_question_is_valid(self):
        serializer = QueryRequestSerializer(data={"question": "Show revenue by region"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["question"], "Show revenue by region")

    def test_missing_question_is_invalid(self):
        serializer = QueryRequestSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("question", serializer.errors)

    def test_empty_string_question_is_invalid(self):
        serializer = QueryRequestSerializer(data={"question": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("question", serializer.errors)

    def test_whitespace_only_question_is_invalid(self):
        # DRF's CharField with trim_whitespace=True (the default) reduces this
        # to blank, so it should be caught by the same blank check.
        serializer = QueryRequestSerializer(data={"question": "     "})
        self.assertFalse(serializer.is_valid())
        self.assertIn("question", serializer.errors)

    def test_question_over_500_chars_is_invalid(self):
        serializer = QueryRequestSerializer(data={"question": "a" * 501})
        self.assertFalse(serializer.is_valid())
        self.assertIn("question", serializer.errors)

    def test_question_at_exactly_500_chars_is_valid(self):
        serializer = QueryRequestSerializer(data={"question": "a" * 500})
        self.assertTrue(serializer.is_valid())

    def test_non_string_question_is_invalid(self):
        serializer = QueryRequestSerializer(data={"question": {"nested": "object"}})
        self.assertFalse(serializer.is_valid())
        self.assertIn("question", serializer.errors)

    def test_custom_error_message_for_missing_field(self):
        serializer = QueryRequestSerializer(data={})
        serializer.is_valid()
        self.assertEqual(str(serializer.errors["question"][0]), "The question field is mandatory.")

    def test_custom_error_message_for_blank_field(self):
        serializer = QueryRequestSerializer(data={"question": ""})
        serializer.is_valid()
        self.assertEqual(str(serializer.errors["question"][0]), "Your question cannot be empty.")