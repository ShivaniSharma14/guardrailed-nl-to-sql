import os
from openai import OpenAI
from django.core.exceptions import ValidationError

class LLMQueryService:
    """
    Acts as a pure translation gateway. It takes the natural language question
    and schema context, formats an enterprise-guarded system prompt,
    and returns a raw candidate SQL string.
    """

    def __init__(self):
        
        self.api_key = os.getenv("AI_PROVIDER_API_KEY")
        self.base_url = os.getenv("AI_PROVIDER_BASE_URL", "https://api.groq.com/openai/v1")
        self.model_name = os.getenv("AI_MODEL_NAME", "llama-3.3-70b-versatile")

        if not self.api_key:
            # Prevent the pipeline from executing if the environment is misconfigured
            raise ValidationError("Configuration Error: Missing AI_PROVIDER_API_KEY in environment variables.")

        # Initialize the universal client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_sql(self, user_question: str, schema_context: str) -> str:
        """
        Sends the prompt to the AI provider and extracts the raw SQL block.
        """
        
        # 💡 The Heart of NL-to-SQL: The System Guardrail Prompt
        system_prompt = f"""
You are a strict, high-performance PostgreSQL database assistant.
Your sole job is to translate the user's natural language question into a single, valid, read-only PostgreSQL SELECT query.

{schema_context}

CRITICAL INSTRUCTIONS:
1. Use ONLY the tables and columns listed in the schema context above. Do not guess or hallucinate names.
2. Generate exactly ONE executable SELECT statement.
3. Do not modify, insert, delete, or alter any data (No INSERT, UPDATE, DELETE, DROP, ALTER).
4. Return ONLY the raw SQL code. Do not include markdown blocks like ```sql, do not explain your logic, do not write text outside the query.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Translate this question to SQL: {user_question}"}
                ],
                temperature=0.0, # Force deterministic output, minimize creative hallucinations!
                max_tokens=300
            )
            
            raw_sql = response.choices[0].message.content.strip()
            
            # Clean up trailing markdown symbols if the model accidentally violates constraints
            if raw_sql.startswith("```"):
                raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
                
            return raw_sql

        except Exception as e:
            raise ValidationError(f"AI Provider Service Failure: Unable to generate query. Details: {e}")
