from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView

from . import views

urlpatterns = [
    path('register', views.CreateUserView.as_view(), name='index'),
    path('login', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('verify', TokenVerifyView.as_view(), name='token_verify')
]
