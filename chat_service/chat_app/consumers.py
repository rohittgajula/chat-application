
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from datetime import datetime

class RoomConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"
        self.user = None

        # verify user auth
        user = self.scope.get('user')
        if user and user.is_authenticated:
            self.user = user
            user_info = {
                'id': user.id,
                'username': getattr(user, 'username', 'unknown')
            }
        else:
            user_info = {'id': None, 'username': 'Anonymous'}

        room_exists = await self.check_room_exists(self.room_id)
        if not room_exists:
            await self.close(code=4404)
            return

        # join the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'WebSocket connected to room {self.room_id}',
            'room_id': self.room_id,
            'room_group_name': self.room_group_name,
            'user_info': user_info,
            'timestamp': datetime.now().isoformat(),
            'status': 'connected'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'unknown')

            if message_type == 'ping':
                # Handle ping for connection health check
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }))

            elif message_type == 'info':
                # Send room info
                await self.send(text_data=json.dumps({
                    'type': 'room_info',
                    'room_id': self.room_id,
                    'room_group_name': self.room_group_name,
                    'connected_at': datetime.now().isoformat()
                }))

            elif message_type == 'chat_message':
                # Handle chat message
                await self.handle_chat_message(text_data_json)

            elif message_type == 'typing':
                # Handle typing indicator
                await self.handle_typing_indicator(text_data_json)

            elif message_type == 'message_status':
                # Handle message status update
                await self.handle_message_status(text_data_json)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': "Invalid JSON format",
                'code': 'INVALID_JSON'
            }))
        except KeyError as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': f"Missing required fields: {str(e)}",
                'code': 'MISSING_FIELDS'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': f"Server error: {str(e)}",
                'code': 'SERVER_ERROR'
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        content = data.get('content', '').strip()
        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Message content is required',
                'code': 'EMPTY_CONTENT'
            }))
            return

        message_type = data.get('message_type', 'text')
        file_url = data.get('file_url')
        mentions = data.get('mentions', [])

        # Get user info from scope (set by middleware)
        user_data = self.scope.get('user_data')
        if not user_data:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }))
            return

        # Save message to database
        message = await self.save_message(
            content=content,
            message_type=message_type,
            file_url=file_url,
            mentions=mentions,
            sender_id=user_data['id']
        )

        if message:
            # Broadcast message to other room members (excluding sender)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': {
                        'id': str(message.id),
                        'sender': {
                            'id': user_data['id'],
                            'username': user_data['username']
                        },
                        'content': message.content,
                        'message_type': message.message_type,
                        'file_url': message.file_url,
                        'mentions': message.mentions,
                        'created_at': message.created_at.isoformat(),
                        'is_edited': message.is_edited
                    },
                    'sender_channel': self.channel_name  # Exclude sender
                }
            )

    async def handle_typing_indicator(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        user_data = self.scope.get('user_data')

        if user_data:
            # Broadcast typing indicator to other room members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator_broadcast',
                    'user': {
                        'id': user_data['id'],
                        'username': user_data['username']
                    },
                    'is_typing': is_typing,
                    'sender_channel': self.channel_name  # Don't send back to sender
                }
            )

    async def handle_message_status(self, data):
        """Handle message status update (delivered/seen)"""
        message_id = data.get('message_id')
        status = data.get('status')

        if not message_id or not status:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'message_id and status are required',
                'code': 'MISSING_STATUS_FIELDS'
            }))
            return

        if status not in ['sent', 'delivered', 'seen']:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Invalid status. Must be: sent, delivered, seen',
                'code': 'INVALID_STATUS'
            }))
            return

        user_data = self.scope.get('user_data')
        if not user_data:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }))
            return

        # Update message status in database
        updated = await self.update_message_status(message_id, user_data['id'], status)

        if updated:
            # Broadcast status update to message sender (not all room members)
            message_info = await self.get_message_sender(message_id)
            if message_info:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_status_broadcast',
                        'message_id': str(message_id),
                        'status': status,
                        'user': {
                            'id': str(user_data['id']),
                            'username': user_data['username']
                        },
                        'sender_id': str(message_info['sender_id'])  # Only send to message sender
                    }
                )
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Message not found or status update failed',
                'code': 'STATUS_UPDATE_FAILED'
            }))

    async def chat_message_broadcast(self, event):
        """Send message to WebSocket (excluding sender)"""
        # Don't send the message back to the sender
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'new_message',
                'message': event['message']
            }))

    async def typing_indicator_broadcast(self, event):
        """Send typing indicator to WebSocket (except sender)"""
        # Don't send typing indicator back to the person who's typing
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))

    async def message_status_broadcast(self, event):
        """Send message status update to message sender only"""
        user_data = self.scope.get('user_data')
        # Only send status update to the original message sender
        if user_data and user_data['id'] == event['sender_id']:
            await self.send(text_data=json.dumps({
                'type': 'message_status_update',
                'message_id': event['message_id'],
                'status': event['status'],
                'user': event['user']
            }))

    @database_sync_to_async
    def save_message(self, content, message_type, file_url, mentions, sender_id):
        """Save message to database"""
        from .models import Message, Room
        try:
            room = Room.objects.get(room_id=self.room_id)
            message = Message.objects.create(
                room=room,
                sender=sender_id,
                content=content,
                message_type=message_type,
                file_url=file_url,
                mentions=mentions
            )
            return message
        except Room.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def update_message_status(self, message_id, user_id, status):
        """Update or create message status"""
        from .models import Message, MessageStatus
        import uuid
        try:
            # Convert string UUID to UUID object if needed
            if isinstance(message_id, str):
                message_id = uuid.UUID(message_id)
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)

            message = Message.objects.get(id=message_id)
            message_status, created = MessageStatus.objects.get_or_create(
                message=message,
                user=user_id,
                defaults={'status': status}
            )
            if not created:
                message_status.status = status
                message_status.save()
            return True
        except (Message.DoesNotExist, ValueError):
            return False
        except Exception as e:
            print(f"Error updating message status: {e}")
            return False

    @database_sync_to_async
    def get_message_sender(self, message_id):
        """Get message sender info"""
        from .models import Message
        try:
            message = Message.objects.get(id=message_id)
            return {'sender_id': str(message.sender)}
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def check_room_exists(self, room_id):
        from .models import Room
        try:
            Room.objects.get(room_id=room_id)
            return True
        except Room.DoesNotExist:
            return False