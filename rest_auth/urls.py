from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView

from rest_auth.views import MyTokenObtainPairView
from . import views

router = routers.DefaultRouter()
router.register(r'userprofile', views.UserProfileViewSet)

urlpatterns = [
    path('',include(router.urls)),
    path('getuserprofile', views.GetUserProfile.as_view()),
    path('register', views.CreateUserView.as_view(), name='index'),
    path('login', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('verify', TokenVerifyView.as_view(), name='token_verify')
]
