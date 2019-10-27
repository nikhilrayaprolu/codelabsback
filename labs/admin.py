from django.contrib import admin

# Register your models here.
from labs.models import Topic, Track, Challenge, TopicTrackMapping, TrackChallengeMapping, ContainerData, \
    SubmittedAssignments

admin.site.register(Topic)
admin.site.register(Track)
admin.site.register(Challenge)
admin.site.register(TopicTrackMapping)
admin.site.register(TrackChallengeMapping)
admin.site.register(ContainerData)
admin.site.register(SubmittedAssignments)

