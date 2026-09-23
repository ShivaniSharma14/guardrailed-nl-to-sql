from rest_framework import serializers
from .models import QueryLog

class QueryRequestSerializer(serializers.Serializer):
    # Strict validation guardrails for the natural language input
    question = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=500,  # Guard against buffer or context stuffing attacks
        error_messages={
            "required": "The question field is mandatory.",
            "blank": "Your question cannot be empty.",
            "max_length": "Your question is too long. Please keep it under 500 characters.",
        },
    )

class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = [
            "id", "question", "validated_secure_sql", "status",
            "error_code", "row_count", "latency_ms", "created_at",
        ]
        read_only_fields = fields