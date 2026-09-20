"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from src.guardrailed_nl_to_sql.views import health_check
from queries.views import NaturalLanguageQueryView
from users.views import UserRegisterView, CustomLoginView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", UserRegisterView.as_view(), name="auth_register"), # Map registration view here
    path("api/auth/login/", CustomLoginView.as_view(), name="auth_login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("api/query/", NaturalLanguageQueryView.as_view(), name="nl-to-sql"),
    path("api/health/", health_check, name="health_check"),
]
