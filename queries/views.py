from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from queries.serializers import QueryRequestSerializer
from queries.services.schema_discovery import SchemaDiscoveryService


class NaturalLanguageQueryView(APIView):
    # Core MVP Requirement: Only verified logged-in users can execute queries
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Parse payload structure via serializer
        serializer = QueryRequestSerializer(data=request.data)

        # Halt immediately if input is empty or invalid
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Extract the sanitized string
        user_question = serializer.validated_data["question"]

        # Fire the database discovery agent you just coded
        schema_discoverer = SchemaDiscoveryService()
        current_schema_context = schema_discoverer.discover_schema()

        # Return compilation checkpoint success
        return Response(
            {
                "status": "success",
                "validated_question": user_question,
                "discovered_schema_context": current_schema_context,
                "next_steps": "Send this schema context + question to the LLM generation layer.",
            },
            status=status.HTTP_200_OK,
        )
