from django.urls import path

from . import views

urlpatterns = [
    path('newlab/', views.NewLab.as_view(), name='newlab'),
    path('trackslist/', views.Trackslist.as_view(), name='tracklist'),
    path('gettrack/<int:trackid>', views.Gettrack.as_view(), name='gettrack'),
    path('runtrack/<int:trackid>/<int:courseid>/<int:studentid>', views.RunTrack.as_view(), name='runtrack'),
    path('runtrack/<int:trackid>/<int:courseid>', views.RunTrack.as_view(), name='runtrack'),
    path('runtrack/<int:trackid>', views.RunTrack.as_view(), name='runtrack'),
    path('buildtrack/<int:trackid>', views.BuildTrack.as_view(), name='buildtrack'),
    path('keepcontaineralive/<int:containerid>', views.KeepContainerAlive.as_view(), name='keepcontaineralive')
]
