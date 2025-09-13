import os
import requests
from functools import wraps
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, APIView

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL")

def check_user(token):
    try:
        from django.conf import settings
        
        if not AUTH_SERVICE_URL:
            return None
        
        # Use microservice endpoint with service authentication
        response = requests.post(
            f"{AUTH_SERVICE_URL}/users/verify-token/", 
            headers={
                "X-Service-Key": getattr(settings, 'MICROSERVICE_SECRET_KEY', ''),
                "Content-Type": "application/json"
            },
            json={"token": token},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                return data.get('user')
        return None
    except Exception as e:
        print(f"Auth service error: {e}")
        return None

def require_auth(view_func):                # decorator
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Authorization header required'
            }, status=401)
        
        token = auth_header.split(' ')[1]
        user_data = check_user(token)
        
        if not user_data:
            return JsonResponse({
                'error': 'Invalid or expired token'
            }, status=401)
        
        # Add user data to request for use in view
        request.user_data = user_data
        return view_func(request, *args, **kwargs)
    
    return wrapper

@api_view(['GET'])
@require_auth
def protected_test(request):            # test endpoint requires auth
    return Response({
        "message": "Authentication successful!",
        "user": request.user_data
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def test_auth(request):                 # test endpoint without auth
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({
            'error': 'Authorization header required',
            'format': 'Authorization: Bearer <token>'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    token = auth_header.split(' ')[1]
    user_data = check_user(token)
    
    if user_data:
        return Response({
            'message': 'Token is valid',
            'user': user_data,
            'auth_service_url': AUTH_SERVICE_URL
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid or expired token',
            'auth_service_url': AUTH_SERVICE_URL
        }, status=status.HTTP_401_UNAUTHORIZED)
