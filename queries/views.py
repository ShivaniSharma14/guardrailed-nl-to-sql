from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from queries.serializers import QueryRequestSerializer
from queries.services.llm_service import LLMQueryService
from queries.services.schema_discovery import SchemaDiscoveryService
from queries.services.sql_executor import SQLExecutorService
from queries.services.sql_validator import SQLValidatorService


class NaturalLanguageQueryView(APIView):
    # Core MVP Requirement: Only verified logged-in users can execute queries
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        serializer = QueryRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Extract the sanitized string
        user_question = serializer.validated_data["question"]

        try:
            # Dynamic Runtime Schema Reflection
            schema_discoverer = SchemaDiscoveryService()
            schema_context = schema_discoverer.discover_schema()

            # llm sql translation
            llmService = LLMQueryService()
            candidate_sql = llmService.generate_sql(user_question, schema_context)

            # validating llm generated sql queries
            sqlValidator = SQLValidatorService()
            sanitized_sql = sqlValidator.validate_query(candidate_sql)

            # executing the validated query
            sqlExecutor = SQLExecutorService()
            query_results = sqlExecutor.execute_query(sanitized_sql)

            return Response(
                {
                    "status": "success",
                    "user_question": user_question,
                    "ai_proposed_sql": candidate_sql,
                    "validated_secure_sql": sanitized_sql,
                    "data": query_results,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
