from django.urls import path

from . import views

urlpatterns = [
    path('newlab/', views.NewLab.as_view(), name='newlab'),
    path('trackslist/', views.Trackslist.as_view(), name='tracklist'),
    path('publictrackslist/', views.PublicTrackslist.as_view(), name='publictracklist'),
    path('copytrack/<int:trackid>', views.Copytrack.as_view(), name='copytrack'),
    path('gettrack/<int:trackid>', views.Gettrack.as_view(), name='gettrack'),
    path('getchallenge/<int:challengeid>', views.GetChallenge.as_view(), name='getchallenge'),
    path('getchallenge', views.GetChallenge.as_view(), name='getchallenge'),
    path('runtrack/<int:trackid>/<str:courseid>/<str:studentid>', views.RunTrack.as_view(), name='runtrack'),
    path('runtrack/<int:trackid>/<str:courseid>', views.RunTrack.as_view(), name='runtrack'),
    path('runtrack/<int:trackid>', views.RunTrack.as_view(), name='runtrack'),
    path('buildtrack/<int:trackid>', views.BuildTrack.as_view(), name='buildtrack'),
    path('keepcontaineralive/<str:containerid>', views.KeepContainerAlive.as_view(), name='keepcontaineralive'),
    path('submitlab/<int:trackid>/<str:courseid>/<str:studentid>', views.SubmitLab.as_view(), name='submitlab'),
    path('snapshotcontainer/<str:containerid>/<int:trackid>', views.SnapShotContainer.as_view(), name='snapshotcontainer'),
    path('fileupload/<int:trackid>/<str:filename>', views.FileUploadView.as_view()),
    path('fileupload/<int:trackid>/<str:filename>/<str:courseid>/<str:studentid>', views.FileUploadView.as_view()),
    path('filedownload/<int:trackid>/<str:courseid>/<str:studentid>', views.FileDownload.as_view()),
    path('resetfile/<int:trackid>/<str:courseid>/<str:studentid>', views.ResetFolder.as_view()),
    path('startiframe/<str:containerid>/<int:port>', views.StartIframe.as_view()),
    path('evaluatecoursetrack/<str:courseid>/<int:trackid>', views.EvaluatorTrackCourseStats.as_view()),
    path('evaluatecourse/<str:courseid>', views.EvaluatorCourseStats.as_view()),
    path('evaluate/', views.EvaluatorStats.as_view()),
    path('submissions/<int:submissionid>', views.SubmissionsView.as_view()),
    path('gradesubmissions/<int:submissionid>/<str:grade>', views.SubmissionsGrader.as_view())
]
