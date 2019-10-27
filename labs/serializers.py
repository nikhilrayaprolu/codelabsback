from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Topic, Track, Challenge, TopicTrackMapping, TrackChallengeMapping, ContainerData, \
    SubmittedAssignments


class TopicSerializer(serializers.ModelSerializer):
    user_created = serializers.StringRelatedField(default=serializers.CurrentUserDefault(), read_only=True)
    class Meta:
        model = Topic
        fields = '__all__'

class TrackSerializer(serializers.ModelSerializer):
    user_created = serializers.StringRelatedField(default=serializers.CurrentUserDefault(), read_only=True)
    topic = serializers.StringRelatedField()
    class Meta:
        model = Track
        fields = '__all__'

class ChallengeSerializer(serializers.ModelSerializer):
    user_created = serializers.StringRelatedField(default=serializers.CurrentUserDefault(), read_only=True)
    class Meta:
        model = Challenge
        fields = '__all__'

class TopicTrackMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicTrackMapping
        fields = '__all__'

class TrackChallengeMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackChallengeMapping
        fields = '__all__'

class ContainerDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerData
        fields = '__all__'

class SubmittedAssignmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmittedAssignments
        fields = '__all__'
