from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    # Enforce password visibility constraints and write-only safety
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]  # Uses Django's native password strength validators
    )

    class Meta:
        model = User
        fields = ("email", "password")

    def create(self, validated_data):
        # Use create_user to hash the password securely, never use create()
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"]
        )
        return user
