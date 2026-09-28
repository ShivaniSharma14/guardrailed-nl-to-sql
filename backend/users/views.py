from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  
from .serializers import UserRegisterSerializer
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "User registered successfully.",
                    "user": {
                        "id": user.id,
                        "email": user.email
                    }
                }, 
                status=status.HTTP_201_CREATED
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CustomLoginView(APIView):
    permission_classes = [AllowAny]  # 🔓 Publicly accessible

    def post(self, request, *args, **kwargs):
        # Explicitly extract custom email and password fields from the incoming payload
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Please provide both email and password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate using Django's native system (looks at your CustomUser model)
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Generate cryptographic tokens directly for this authenticated user
            refresh = RefreshToken.for_user(user)
            return Response({
                "status": "success",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": str(user.id),
                    "email": user.email
                }
            }, status=status.HTTP_200_OK)
            
        return Response(
            {"error": "Invalid email or password credentials."},
            status=status.HTTP_401_UNAUTHORIZED
        )

