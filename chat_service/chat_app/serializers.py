from rest_framework import serializers
from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['room_id', 'room_name', 'is_group', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['room_id', 'created_by', 'created_at', 'updated_at']


class CreateRoomSerializer(serializers.ModelSerializer):
    usernames = serializers.ListField(
        child=serializers.CharField(max_length=150),
        min_length = 1,
        help_text="List of usernames to add to room"
    )

    class Meta:
        model = Room
        fields = ['room_name', 'is_group', 'description', 'usernames']
        extra_kwargs = {
            'room_name': {'required': False}
        }

    def validate(self, data):
        usernames = data.get("usernames", [])
        # room_name = data.get("room_name")
        is_group = data.get("is_group", False)

        if not is_group and len(usernames) != 1:
            raise serializers.ValidationError("Direct message requires exactly 1 user")
        
        if is_group and len(usernames) < 1:
            raise serializers.ValidationError("Group rooms requires atleast 1 another person")

        # if is_group and not room_name:
        #     raise serializers.ValidationError("Group rooms require a room name")
        
        return data


