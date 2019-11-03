from rest_framework import permissions, viewsets
from rest_framework.generics import CreateAPIView
from django.contrib.auth import get_user_model # If used custom user model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_auth.models import UserMiniProfile
from .serializers import UserSerializer, UserMiniProfileSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class CreateUserView(CreateAPIView):

    model = get_user_model()
    permission_classes = [
        permissions.AllowAny # Or anon users can't register
    ]
    serializer_class = UserSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['name'] = user.username
        # ...

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user profile instances.
    """
    serializer_class = UserMiniProfileSerializer
    queryset = UserMiniProfile.objects.all()

class GetUserProfile(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_profile = request.user.mini_user_profile
            if user_profile:
                user_profile_serializer = UserMiniProfileSerializer(user_profile)
                return Response(user_profile_serializer.data, status=200)
            else:
                return Response({}, status=200)
        except:
            return Response({}, status=200)


