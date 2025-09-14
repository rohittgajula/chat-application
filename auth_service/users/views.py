from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, APIView, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from .models import CustomUser, Contact
from .serializers import ProfileSerializer, CreateUpdateSerializer, VerifyAcountSerializer
from rest_framework import status
from .tasks import send_otp_via_mail, otp_timer
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_details(request):
    user = request.user
    serializer = ProfileSerializer(user)
    return Response({
        "user":serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    try:
        data = request.data
        serializer = CreateUpdateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            send_otp_via_mail.delay(serializer.data['email'])
            otp_timer.apply_async((serializer.data['email'],), countdown=600)
            return Response({
                "message": f"Registered sucessfully. OTP sent to {data['email']}, expires in 10min",
                'data':serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message":"Something went wrong.",
                "error":serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "message":"Something went wrong while registration",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_otp(request):
    try:
        user = request.user
        data = request.data
        otp = data.get('otp')
        
        if not otp:
            return Response({
                "message":"OTP is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.otp != otp:
            return Response({
                "message":"Wrong OTP."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.is_verified = True
            user.save()
            return Response({
                'message':"Account verified."
            }, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        return Response({
            "message":"Error occured while verifying.",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resend_otp(request):
    user = request.user
    print(f"user: {user}")
    email = user.email
    send_otp_via_mail.delay(email)
    otp_timer.apply_async((email, ), countdown = 600)
    return Response({
        'message':'OTP sent successfully, Expires in 10min.'
    }, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token_microservice(request):
    from django.conf import settings
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    
    service_key = request.headers.get('X-Service-Key')
    if service_key != getattr(settings, 'MICROSERVICE_SECRET_KEY', None):
        return Response({
            'error': 'Unauthorized service'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    token = request.data.get('token')
    if not token:
        return Response({
            'error': 'Token required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        
        user = CustomUser.objects.get(id=user_id)
        serializer = ProfileSerializer(user)
        
        return Response({
            'valid': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    except (InvalidToken, TokenError, CustomUser.DoesNotExist) as e:
        return Response({
            'valid': False,
            'error': str(e)
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                "message": "Logout Sucessfull."
            })

        except Exception as e:
            return Response({
                "error": f"Invalid token: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([AllowAny])
def search_by_username(request):
    usernames = request.data.get('usernames', [])
    print(f"AUTH SERVICE: usernames: {usernames}")
    if not isinstance(usernames, list) or not usernames:
        return Response({
            "error": "usernames must be a non-empty list"
        }, status=status.HTTP_400_BAD_REQUEST)
    print(f"AUTH SERVICE: *********")
    users = CustomUser.objects.filter(username__in=usernames)
    print(f"AUTH SERVICE: matched users : {users}")
    serializer = ProfileSerializer(users, many=True)
    return Response({
        "valid": True,
        "users": serializer.data
    }, status=status.HTTP_200_OK)

