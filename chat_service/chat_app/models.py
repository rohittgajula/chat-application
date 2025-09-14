from django.db import models
import uuid



class Room(models.Model):
    room_id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    room_name = models.CharField(max_length=30, blank=False, null=False)
    description = models.CharField(max_length=350, blank=True, null=True)
    is_group = models.BooleanField(default=False)
    room_avatar = models.URLField(max_length=500, blank=True, null=True)
    created_by = models.UUIDField(null=False, blank=False, help_text="Reference to User ID from auth service")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_group', '-updated_at']),
            models.Index(fields=['created_at'])
        ]

    @classmethod
    def get_or_create_direct_room(cls, user1_id, user2_id, room_name=None):
        from django.db import models as django_models
        
        # Check if room already exists between these users
        existing_rooms = cls.objects.filter(
            is_group=False,
            roommembers__user__in=[user1_id, user2_id]
        ).annotate(
            member_count=django_models.Count('roommembers')
        ).filter(member_count=2)
        
        for room in existing_rooms:
            users = list(room.roommembers.values_list('user', flat=True))
            if set(users) == {user1_id, user2_id}:
                return room, False

        if room_name is None:
            room_name = f"Direct message"
        
        # Create new room if none exists
        room = cls.objects.create(
            room_name=room_name,
            is_group=False,
            created_by=user1_id
        )
        
        # Add both users as members
        from .models import RoomMembers
        RoomMembers.objects.create(room=room, user=user1_id, role="admin")
        RoomMembers.objects.create(room=room, user=user2_id, role="user")
        
        return room, True




class RoomMembers(models.Model):
    ROOM_MEMBER_ROLE = [
        ("admin", "Admin"),
        ("user", "User")
    ]
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.UUIDField(null=False, blank=False, help_text="Reference to User ID from auth service")
    role = models.CharField(max_length=20, choices=ROOM_MEMBER_ROLE, default="user")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'user')
        indexes = [
              models.Index(fields=['user', 'room']),
              models.Index(fields=['room', 'role']),
          ]

class Message(models.Model):
    MESSAGE_TYPES=[
        ("text", "Text"),
        ("image", "Image"),
        ("file", "File")
    ]
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.UUIDField(blank=False, null=False, help_text="Reference to User ID from auth service")
    content = models.TextField(null=True, blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default="text")
    file_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    mentions = models.JSONField(default=list, blank=True, help_text="List of mentioned users uuid's")

    class Meta:
        ordering = ['-created_at']
        indexes = [
              models.Index(fields=['room', '-created_at']),
              models.Index(fields=['sender', '-created_at']),
              models.Index(fields=['room', 'is_deleted', '-created_at']),
          ]

    def __str__(self):
          return f"Message from {self.sender} in {self.room.room_name}"
  
class MessageStatus(models.Model):
    STATUS=[
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("seen", "Seen")
    ]
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.UUIDField(blank=False, null=False, help_text="Reference to User ID from auth service")
    status = models.CharField(max_length=20, choices=STATUS, default="sent")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
          unique_together = ('message', 'user')  # One status per user per message
          indexes = [
              models.Index(fields=['message', 'user']),
              models.Index(fields=['user', 'status']),
          ]



class RoomSettings(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='settings')
    max_members = models.IntegerField(default=100)
    is_private = models.BooleanField(default=False)
    allow_file_sharing = models.BooleanField(default=False)


class UserActivity(models.Model):
    user = models.UUIDField(help_text="Reference to User ID from auth service")
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    last_seen = models.DateTimeField(auto_now=True)
    is_typing = models.BooleanField(default=False)
    typing_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
          unique_together = ('user', 'room')  # One activity record per user per room
  
          indexes = [
              models.Index(fields=['room', 'last_seen']),
              models.Index(fields=['user', 'is_typing']),
          ]


