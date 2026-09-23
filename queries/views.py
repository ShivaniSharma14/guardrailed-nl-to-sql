import time
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from queries.serializers import QueryRequestSerializer, QueryLogSerializer
from queries.services.llm_service import LLMQueryService
from queries.services.schema_discovery import SchemaDiscoveryService
from queries.services.sql_executor import SQLExecutorService
from queries.services.sql_validator import SQLValidatorService
from queries.models import QueryLog
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

class NaturalLanguageQueryView(APIView):
    # Core MVP Requirement: Only verified logged-in users can execute queries
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        # Start the performance telemetry timer
        start_time = time.perf_counter()

        serializer = QueryRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Extract the sanitized string
        user_question = serializer.validated_data["question"]

        # Create the record instantly as 'processing' to capture the request entry
        log_entry = QueryLog.objects.create(
            user=request.user,
            question=user_question,
            status="processing"
        )

        try:
            # Dynamic Runtime Schema Reflection
            schema_discoverer = SchemaDiscoveryService()
            schema_context = schema_discoverer.discover_schema()

            # llm sql translation
            llmService = LLMQueryService()
            candidate_sql = llmService.generate_sql(user_question, schema_context)
            log_entry.ai_proposed_sql = candidate_sql

            # validating llm generated sql queries
            sqlValidator = SQLValidatorService()
            sanitized_sql = sqlValidator.validate_query(candidate_sql)
            log_entry.validated_secure_sql=sanitized_sql

            # executing the validated query
            sqlExecutor = SQLExecutorService()
            query_results = sqlExecutor.execute_query(sanitized_sql)

            # Calculate performance telemetry metrics
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            row_count = len(query_results)
            
            # Flip the 'processing' flag to 'success' and save performance metrics
            log_entry.status = "success"
            log_entry.row_count = row_count
            log_entry.latency_ms = latency_ms
            log_entry.save()

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
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            error_str = str(e)
            
            # Determine the standardized error code and classification
            if "Security Violation" in error_str:
                log_status = "blocked"
                error_code = "SQL_GUARDRAIL_VIOLATION"
                clean_message = "The generated query was rejected by system security policies."
            elif "Result Limit Exceeded" in error_str:
                log_status = "blocked"
                error_code = "RESULT_LIMIT_EXCEEDED"
                clean_message = "The query results exceeded the maximum allowed rows and was blocked."
            elif "Database Runtime Exception" in error_str:
                log_status = "failed"
                error_code = "DATABASE_EXECUTION_ERROR"
                clean_message = "The query encountered a runtime error inside the database execution pool."
            else:
                log_status = "failed"
                error_code = "PIPELINE_EXCEPTION"
                clean_message = "An unexpected error occurred while processing the request pipeline."
            
            # Update the record to reflect the exact security block or failure cleanly
            log_entry.status = log_status
            log_entry.error_code = error_code
            log_entry.error_message = clean_message
            log_entry.latency_ms = latency_ms
            log_entry.save()
            
            return Response({
                "error": clean_message, 
                "error_code": error_code
            }, status=status.HTTP_400_BAD_REQUEST)
            
class QueryHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class QueryHistoryView(ListAPIView):
    serializer_class = QueryLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = QueryHistoryPagination

    def get_queryset(self):
        return QueryLog.objects.filter(user=self.request.user).order_by("-created_at")