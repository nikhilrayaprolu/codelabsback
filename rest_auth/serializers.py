from rest_framework import serializers
from django.contrib.auth import get_user_model # If used custom user model

from rest_auth.models import UserMiniProfile

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    def create(self, validated_data):

        user = UserModel.objects.create(
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()

        return user

    class Meta:
        model = UserModel
        # Tuple of serialized model fields (see link [2])
        fields = ( "id", "username", "password", )

class UserMiniProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMiniProfile
        fields = '__all__'
