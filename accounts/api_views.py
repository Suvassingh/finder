import logging
import google.auth.transport.requests
import google.oauth2.id_token

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def _token_response(user):
    """Return JWT access + refresh token dict for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


#  Signup 

class SignupThrottle(ScopedRateThrottle):
    scope = 'signup'


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@permission_classes([AllowAny])
@throttle_classes([SignupThrottle])
def signup_api(request):
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    email = data['email'].lower().strip()

    user = User.objects.create_user(
        username=email,
        email=email,
        password=data['password'],
        first_name=data.get('name', ''),
    )

    profile = user.profile
    profile.phone = data.get('phone', '')
    if data.get('latitude') is not None:
        profile.latitude = data['latitude']
    if data.get('longitude') is not None:
        profile.longitude = data['longitude']
    if data.get('profile_image'):
        profile.profile_image = data['profile_image']
    profile.save()

    logger.info("New user registered: %s", email)

    return Response({
        "message": "Signup successful",
        "user": UserSerializer(user, context={'request': request}).data,
        "tokens": _token_response(user),
    }, status=201)


#  Login 

class LoginThrottle(ScopedRateThrottle):
    scope = 'login'


@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([AllowAny])  
@throttle_classes([LoginThrottle])
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    user = authenticate(username=data['email'], password=data['password'])

    if not user:
        return Response({"error": "Invalid email or password."}, status=401)

    if not user.is_active:
        return Response({"error": "This account has been disabled."}, status=403)

    logger.info("User logged in: %s", data['email'])

    return Response({
        "message": "Login successful",
        "user": UserSerializer(user, context={'request': request}).data,
        "tokens": _token_response(user),
    })


# ─── Google Sign-In ──────────────────────────────────────────────────────────

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([AllowAny])

def google_signin_api(request):
    id_token_str = request.data.get('id_token')
    if not id_token_str:
        return Response({"error": "id_token is required."}, status=400)

    try:
        request_adapter = google.auth.transport.requests.Request()
        decoded = google.oauth2.id_token.verify_oauth2_token(
            id_token_str,
            request_adapter,
            settings.GOOGLE_OAUTH2_CLIENT_ID,
        )
    except ValueError:
        return Response({"error": "Invalid or expired Google token."}, status=400)
    except Exception as e:
        logger.exception("Google token verification failed")
        return Response({"error": "Token verification failed."}, status=500)

    email = decoded.get('email', '').lower().strip()
    if not email:
        return Response({"error": "Email not provided by Google."}, status=400)

    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            'email': email,
            'first_name': decoded.get('given_name', ''),
            'last_name': decoded.get('family_name', ''),
        },
    )
    if created:
        user.set_unusable_password()
        user.save()
        logger.info("New Google user created: %s", email)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if 'phone' in request.data:
        profile.phone = request.data['phone']
    if 'latitude' in request.data:
        try:
            profile.latitude = float(request.data['latitude'])
        except (ValueError, TypeError):
            pass
    if 'longitude' in request.data:
        try:
            profile.longitude = float(request.data['longitude'])
        except (ValueError, TypeError):
            pass
    if 'custom_location' in request.data:
        profile.custom_location = request.data['custom_location']
    if 'profile_image' in request.FILES:
        profile.profile_image = request.FILES['profile_image']
    profile.save()

    return Response({
        "message": "Google sign-in successful",
        "created": created,
        "user": UserSerializer(user, context={'request': request}).data,
        "tokens": _token_response(user),
    })


# ─── Profile ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_api(request, user_id):
    if request.user.id != user_id:
        return Response({"error": "Not authorized to view this profile."}, status=403)

    try:
        user = User.objects.select_related('profile').get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    return Response(UserSerializer(user, context={'request': request}).data)


@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@permission_classes([IsAuthenticated])
def profile_update_api(request, user_id):
    if request.user.id != int(user_id):
        return Response({"error": "Not authorized to update this profile."}, status=403)

    try:
        user = User.objects.select_related('profile').get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    serializer = ProfileUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    profile = user.profile

    if 'name' in data:
        user.first_name = data['name']
        user.save(update_fields=['first_name'])
    if 'phone' in data:
        profile.phone = data['phone']
    if 'latitude' in data:
        profile.latitude = data['latitude']
    if 'longitude' in data:
        profile.longitude = data['longitude']
    if 'custom_location' in data:
        profile.custom_location = data['custom_location']
    if 'bio' in data:
        profile.bio = data['bio']
    if 'profile_image' in request.FILES:
        profile.profile_image = request.FILES['profile_image']
    profile.save()

    return Response({
        "message": "Profile updated successfully.",
        "user": UserSerializer(user, context={'request': request}).data,
    })


# ─── Change Password ──────────────────────────────────────────────────────────

@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """Change password for an authenticated user."""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response({"error": "old_password and new_password are required."}, status=400)

    if not request.user.check_password(old_password):
        return Response({"error": "Current password is incorrect."}, status=400)

    if len(new_password) < 8:
        return Response({"error": "New password must be at least 8 characters."}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    logger.info("Password changed for user: %s", request.user.email)

    return Response({"message": "Password changed successfully."})


# ─── Forgot / Reset Password ─────────────────────────────────────────────────

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([AllowAny]) 
def forgot_password_api(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email = serializer.validated_data['email']

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # Don't reveal whether the email exists
        return Response({"message": "If that email is registered, a reset link has been sent."})

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:8000')
    reset_link = f"{frontend_url}/api/accounts/reset-password/{uid}/{token}/"

    try:
        send_mail(
            subject="Reset Your Password",
            message=(
                f"Hello {user.first_name or 'there'},\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                f"This link will expire in 1 hour. "
                f"If you didn't request this, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", email)
        return Response(
            {"error": "Failed to send reset email. Please try again later."},
            status=500,
        )

    return Response({"message": "If that email is registered, a reset link has been sent."})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def reset_password_api(request, uid, token):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id)
    except Exception:
        return HttpResponse("Invalid reset link.", status=400, content_type="text/html")

    if not PasswordResetTokenGenerator().check_token(user, token):
        return HttpResponse(
            "This link has expired or is invalid. Please request a new password reset.",
            status=400,
            content_type="text/html",
        )

    if request.method == 'GET':
        return HttpResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reset Password</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5;
                           display: flex; justify-content: center; align-items: center;
                           min-height: 100vh; padding: 20px; }
                    .card { background: white; padding: 40px; border-radius: 12px;
                            box-shadow: 0 2px 16px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
                    h2 { margin-bottom: 24px; color: #1a1a1a; }
                    label { display: block; margin-bottom: 6px; font-size: 14px; color: #555; }
                    input { width: 100%; padding: 12px; border: 1px solid #ddd;
                            border-radius: 8px; font-size: 15px; margin-bottom: 20px; }
                    input:focus { outline: none; border-color: #3b82f6; }
                    button { width: 100%; background: #3b82f6; color: white;
                             padding: 12px; border: none; border-radius: 8px;
                             font-size: 15px; cursor: pointer; }
                    button:hover { background: #2563eb; }
                    .hint { font-size: 12px; color: #888; margin-top: -14px; margin-bottom: 16px; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>Reset Password</h2>
                    <form method="POST">
                        <label>New Password</label>
                        <input type="password" name="password" minlength="8"
                               placeholder="Enter new password" required />
                        <p class="hint">At least 8 characters</p>
                        <button type="submit">Reset Password</button>
                    </form>
                </div>
            </body>
            </html>
        """, content_type="text/html")

    # POST
    password = request.data.get('password') or request.POST.get('password', '')
    if not password or len(password) < 8:
        return HttpResponse(
            "Password must be at least 8 characters.",
            status=400,
            content_type="text/html",
        )

    user.set_password(password)
    user.save()
    logger.info("Password reset completed for user: %s", user.email)

    return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Password Reset Successful</title></head>
        <body style="font-family:Arial;max-width:400px;margin:60px auto;padding:20px;text-align:center">
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:40px">
                <h2 style="color:#16a34a">✓ Password Reset Successful</h2>
                <p style="margin-top:12px;color:#555">
                    You can now return to the app and log in with your new password.
                </p>
            </div>
        </body>
        </html>
    """, content_type="text/html")
