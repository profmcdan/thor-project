from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from user.views import UserRegistrationView, UserMeView, UserListView, HealthView

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserMeView.as_view(), name='auth_me'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('health/', HealthView.as_view(), name='health'),
]
