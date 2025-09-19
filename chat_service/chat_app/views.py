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
        "message": "Authentication successfull!",
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



def search_user_by_username(usernames):
    try:
        from django.conf import settings

        if not AUTH_SERVICE_URL:
            return []
        
        response = requests.post(
            f"{AUTH_SERVICE_URL}/users/search-by-username/",
            headers={
                "X-Service-Key": getattr(settings, 'MICROSERVICE_SECRET_KEY', ''),
                "Content-Type": "application/json"
            },
            json={"usernames": usernames},
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get('users', [])
        return []

    except Exception as e:
        print(f"User search error: {e}")
        return []


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@api_view(['POST'])
@require_auth
def CreateRoom(request):
    from .serializers import RoomSerializer, CreateRoomSerializer
    from .models import Room, RoomMembers

    data = request.data
    print(f"received data: {data}")
    print(F"CHAT SERVICE: user_data: {request.user_data}")
    serializer = CreateRoomSerializer(data=data)

    if serializer.is_valid():
        usernames = serializer.validated_data['usernames']
        is_group = serializer.validated_data['is_group']
        print(f"CHAT SERVICE: serializer data: {serializer.data}")

        found_users = search_user_by_username(usernames)

        if len(found_users) != len(usernames):
            found_usernames = [user['username'] for user in found_users]
            missing_usernames = list(set(usernames) - set(found_usernames))
            return Response({
                "error": f"users not found: {missing_usernames}"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # get user ids
        other_user_ids = [user['id'] for user in found_users]
        current_user_id = request.user_data['id']
        current_username = request.user_data['username']

        if is_group:
            room = Room.objects.create(
                room_name = serializer.validated_data['room_name'],
                description = serializer.validated_data.get('description', ''),
                is_group=True,
                created_by=current_user_id
            )

            # add creater as admin
            RoomMembers.objects.create(room=room, user=current_user_id, role="admin")

            # add other users
            for user_id in other_user_ids:
                RoomMembers.objects.create(
                    room=room,
                    user=user_id,
                    role="user"
                )
                message = f"Group room created with {len(other_user_ids) + 1} members"
        else:
            other_user_ids=other_user_ids[0]
            other_username = found_users[0]['username']

            room_name = f"chat-{current_username}-{other_username}"

            room, created = Room.get_or_create_direct_room(
                                current_user_id,
                                other_user_ids,
                                room_name=room_name
                        )

            message = "Direct room created successfully" if created else "Room already exists"

        # ============ broadcast room creation for ws ==============

        ws_protocol = 'wss' if request.is_secure() else 'ws'
        host = request.get_host()
        ws_url = f"{ws_protocol}://{host}/ws/chat/{room.room_id}/"

        # ==========================================================

        response_serializer = RoomSerializer(room)
        status_code = status.HTTP_201_CREATED if (is_group or created) else status.HTTP_200_OK

        return Response({
            'message': message,
            'room': response_serializer.data,
            'websocket_url': ws_url,
            'web_socket_info': {
                'room_id': str(room.room_id),
                'room_group_name': f"room_{room.room_id}"
            }
        }, status=status_code)
    
    return Response({
        "error": "Invalid data",
        "details": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


