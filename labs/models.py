from django.db import models
from django.contrib.auth.models import User
import jsonfield

class Topic(models.Model):
    topic = models.CharField(max_length=100)
    tags = models.CharField(max_length=100)
    time_limit = models.TimeField()
    user_created = models.ForeignKey(User, on_delete='CASCADE', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.topic)


class Track(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    container = models.CharField(max_length=100, blank=True, null=True)
    installscript = models.TextField(blank=True, null=True)
    configscript = models.TextField(blank=True, null=True)
    scenario = models.CharField(max_length=100, blank=True, null=True)
    scenario_data = jsonfield.JSONField()
    user_created = models.ForeignKey(User, on_delete='CASCADE', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    topic = models.ForeignKey(Topic, on_delete='CASCADE', related_name='track', blank=True, null=True)
    public = models.BooleanField(default=False)
    final_image = models.CharField(max_length=100, blank=True, null=True)
    labtype = models.CharField(max_length=100, blank=True, null=True)
    colablink = models.CharField(max_length=200, blank=True, null=True)
    uploaded_colab_file_id = models.CharField(max_length=100, blank=True, null=True)

class Challenge(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    setupscript = models.TextField(blank=True, null=True)
    checkscript = models.TextField(blank=True, null=True)
    cleanscript = models.TextField(blank=True, null=True)
    user_created = models.ForeignKey(User, on_delete='CASCADE', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    track = models.ForeignKey(Track, on_delete='CASCADE', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    challenge_position = models.IntegerField(default=0, blank=True, null=True)

class TopicTrackMapping(models.Model):
    topic = models.ForeignKey(Topic, on_delete='CASCADE')
    track = models.ForeignKey(Track, on_delete='CASCADE')

class TrackChallengeMapping(models.Model):
    track = models.ForeignKey(Track, on_delete='CASCADE')
    challenge = models.ForeignKey(Challenge, on_delete='CASCADE')

class ContainerData(models.Model):
    id = models.AutoField(primary_key=True)
    track_id = models.ForeignKey(Track, on_delete='CASCADE')
    course_id = models.CharField(max_length=100)
    student_id = models.CharField(max_length=100)
    container_id = models.CharField(max_length=100, blank=True, null=True)
    container_state = models.CharField(max_length=100, blank=True, null=True)
    container_temp = models.BooleanField(default=True, blank=True, null=True)
    container_ports = jsonfield.JSONField()
    container_run_by_instructor = models.BooleanField(default=False, blank=True, null=True)
    container_last_ping_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    container_colab_file = models.CharField(max_length=100, blank=True, null=True)
    container_colab_webview = models.CharField(max_length=200, blank=True, null=True)
    class Meta:
        unique_together = (('track_id', 'course_id', 'student_id'),)


#Though this model is named Submitted Assignments this is currently used for all kinds of stats for the track
class SubmittedAssignments(models.Model):
    id = models.AutoField(primary_key=True)
    track_id = models.ForeignKey(Track, on_delete='CASCADE', related_name='submittedassignments')
    course_id = models.CharField(max_length=100)
    student_id = models.CharField(max_length=100)
    submit_status = models.CharField(max_length=100)
    container_temp = models.BooleanField(default=True, blank=True, null=True)
    grade = models.FloatField(null=True, blank=True, default=0)
    graded = models.BooleanField(default=False, blank=True, null=True)
    container_colab_file = models.CharField(max_length=100, blank=True, null=True)
    container_colab_webview = models.CharField(max_length=200, blank=True, null=True)
    consumer_key = models.CharField(max_length=100, blank=True, null=True)
    lis_result_sourcedid = models.TextField(blank=True, null=True)
    lis_outcome_service_url = models.TextField(blank=True, null=True)
    class Meta:
        unique_together = (('track_id', 'course_id', 'student_id'),)
