from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    change_password_api,
    forgot_password_api,
    get_profile_api,
    google_signin_api,
    login_api,
    profile_update_api,
    reset_password_api,
    signup_api,
)

urlpatterns = [
    path('signup/', signup_api, name='signup'),
    path('login/', login_api, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('google-signin/', google_signin_api, name='google_signin'),
    path('change-password/', change_password_api, name='change_password'),
    path('profile/<int:user_id>/', get_profile_api, name='get_profile'),
    path('profile/<int:user_id>/update/', profile_update_api, name='profile_update'),
    path('forgot-password/', forgot_password_api, name='forgot_password'),
    path('reset-password/<uid>/<token>/', reset_password_api, name='reset_password'),
]
