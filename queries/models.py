from django.db import models
from django.conf import settings

class QueryLog(models.Model):

    
    STATUS_CHOICES = [
        ("success", "Success"),
        ("processing", "Processing"),
        ("blocked", "Blocked by Guardrails"),
        ("failed", "Execution Failure"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank = True,
        null = True,
        related_name="query_logs",
        db_index=True
    )
    
    # Text input and SQL metadata parameters
    question = models.TextField(help_text="The raw natural language query provided by the client.")
    ai_proposed_sql = models.TextField(
        blank=True, 
        null=True, 
        help_text="The raw, untrusted SQL string generated directly by the LLM."
    )
    validated_secure_sql = models.TextField(
        blank=True, 
        null=True, 
        help_text="The safety-verified and normalized PostgreSQL string emitted by SQLGlot."
    )
    
    # System Status & Error Tracing
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="processing",
        db_index=True
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="A standardized error identifier (e.g., 'SQL_INJECTION_DETECTED', 'DB_TIMEOUT')."
    )
    error_message = models.TextField(
        blank=True, 
        null=True, 
        help_text="A sanitized, safe descriptive string suitable for client-facing exposure."
    )
    
    # Performance Telemetry Analytics
    row_count = models.PositiveIntegerField(
        default=0, 
        help_text="The absolute number of rows retrieved by the secure executor data cursor."
    )
    latency_ms = models.PositiveIntegerField(
        default=0, 
        help_text="Total execution turnaround time profiled in milliseconds."
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "query_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Query {self.id} | User: {self.user.email} | Status: {self.status} | Latency: {self.latency_ms}ms"

