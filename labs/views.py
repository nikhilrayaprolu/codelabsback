import datetime

import os
import docker
from docker import APIClient
import requests

import random
import string

from asgiref.sync import async_to_sync
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
# Create your views here.
from rest_framework_simplejwt.authentication import JWTAuthentication

from labs.models import Track, Challenge, ContainerData
from labs.tasks import build_image
from .serializers import TopicSerializer, TrackSerializer, ChallengeSerializer, TopicTrackMappingSerializer, \
    TrackChallengeMappingSerializer, ContainerDataSerializer

client = docker.from_env()
cli = APIClient()
CERYX_API_ENDPOINT = settings.CERYX_API_ENDPOINT
CONTAINER_HOST = settings.CONTAINER_HOST


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

class Trackslist(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_user_tracks(self, user):
        return Track.objects.filter(user_created=user)

    def get(self, request):
        user = request.user
        user_tracks = self.get_user_tracks(user)
        user_tracks_serializer = TrackSerializer(user_tracks, many=True)
        return Response({'user_tracks': user_tracks_serializer.data}, status=200)

class Gettrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id = id)
    def get(self, request, trackid):
        track = self.get_track_by_id(trackid)
        track_serializer = TrackSerializer(track)
        return Response({'track': track_serializer.data}, status=200)

    def put(self, request, trackid):
        track = request.data
        track = self.get_track_by_id(trackid)
        track_serializer = TrackSerializer(track, data=track)
        if track_serializer.is_valid():
            track_serializer.save()
            return Response({'track': track_serializer.data}, status=200)
        else:
            print(track_serializer.errors)
            return Response(track_serializer.errors, status=200)

    def delete(self, request, trackid):
        track = self.get_track_by_id(trackid)
        track.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RunTrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id=id)

    def get_challenges_by_track(self, track):
        return Challenge.objects.filter(track=track)

    def get_container_if_exists(self, trackid, courseid, studentid):
        try:
            container_data = ContainerData.objects.get(track_id=trackid, course_id=courseid, student_id=studentid)
        except ContainerData.DoesNotExist:
            container_data = None
        return container_data

    def get(self, request, trackid, courseid=None, studentid=None):
        temp = False
        if not courseid:
            courseid = randomString(5)
            temp = True
        if not studentid:
            studentid = randomString(5)
            temp = True
        container_data = None
        if trackid and courseid and studentid:
            container_data = self.get_container_if_exists(trackid, courseid, studentid)
        if not container_data:
            container_data = run_image_from_track_id(trackid, courseid, studentid, temp)
        track = self.get_track_by_id(trackid)
        challenges = self.get_challenges_by_track(trackid)
        track_serializer = TrackSerializer(track)
        challenge_serializer = ChallengeSerializer(challenges, many=True)
        return Response({'track': track_serializer.data, 'challenges': challenge_serializer.data, 'container_data': container_data}, status=200)




class NewLab(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        newlab = request.data
        print(newlab)
        newlab['time_limit'] = str(newlab['timelimit']['hour']) + ':' + str(newlab['timelimit']['minute'])
        print(newlab)
        new_topic_serializer = TopicSerializer(data=newlab, context={'request': request})
        if new_topic_serializer.is_valid():
            new_topic = new_topic_serializer.save()
            for track in newlab['tracks']:
                track['topic'] = new_topic.id
                new_track_serializer = TrackSerializer(data=track, context={'request': request})
                if new_track_serializer.is_valid():
                    new_track = new_track_serializer.save(user_created=self.request.user)
                    print(new_track, "check")
                    topictrackmapping = TopicTrackMappingSerializer(data={'topic':new_topic.id, 'track':new_track.id})
                    if topictrackmapping.is_valid():
                        topictrackmapping.save()
                    else:
                        print(topictrackmapping.errors)
                    for challenge in track['challenges']:
                        challenge['track'] = new_track.id
                        new_challenge_serializer = ChallengeSerializer(data=challenge, context={'request': request})
                        if new_challenge_serializer.is_valid():
                            new_challenge = new_challenge_serializer.save(user_created=self.request.user)
                            print(new_challenge)
                            trackchallengemapping = TrackChallengeMappingSerializer(data={'track':new_track.id, 'challenge':new_challenge.id})
                            if trackchallengemapping.is_valid():
                                trackchallengemapping.save()
                            else:
                                print(trackchallengemapping.errors)
                        else:
                            print(new_challenge_serializer.errors)


                    # image, build_output = build_image(track['container'], track['installscript'])

                else:
                    print(new_track_serializer.errors)

        else:
            print(new_topic_serializer.errors)
        return Response({'success':True}, status=200)

class KeepContainerAlive(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get_container_with_id(self, containerid):
        try:
            container = ContainerData.objects.get(container_id=containerid)
        except ContainerData.DoesNotExist:
            container = None
    def get(self, request, containerid):
        container = self.get_container_with_id(containerid)
        if container:
            container_serializer = ContainerDataSerializer(container, data={'container_last_ping_time': datetime.datetime.now()})
            if container_serializer.is_valid():
                container_serializer.save()
                return Response({'sucess': True, 'container_exists': True}, status=200)
            else:
                print(container_serializer.errors)
                return Response(container_serializer.errors, status=200)
        else:
            return Response({'container_exists': False}, status=200)


class BuildTrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id=id)

    def get(self, request, trackid):
        track = self.get_track_by_id(trackid)
        build_image.delay(track.container, track.installscript, trackid)
        return Response({'sucess': True}, status=200)


def build_image_from_track_id(trackid):
    track = Track.objects.get(id=trackid)
    build_image.delay(track.container, track.installscript, trackid)



def run_image_from_track_id(trackid, courseid=None, studentid=None, temp=False):
    volume_path = os.path.join(os.getcwd(),'public', str(trackid), str(courseid), str(studentid))
    volume = os.makedirs(volume_path, exist_ok=True)

    track = Track.objects.get(id=trackid)
    run_command = "sh -c \"" + track.configscript + " && tail -f /dev/null\""
    print(run_command)
    container, ports = run_lab(track.final_image, run_command, volume_path, str(trackid), str(courseid), str(studentid))
    container_data = {
        'container_id': container.id,
        'course_id': courseid,
        'student_id': studentid,
        'track_id': trackid,
        'container_ports': ports
    }
    if temp:
        container_data['container_temp'] = True

    container_data_serializer = ContainerDataSerializer(data=container_data)
    if container_data_serializer.is_valid():
        container_data_serializer.save()

    return container_data


def run_lab(image, run_command, volume, trackid, courseid, studentid):
    container = client.containers.run(image, run_command, detach=True, network="ceryx", volumes={volume: {'bind': '/wide-node/project', 'mode': 'rw'}})
    ipadress = vars(container)["attrs"]["NetworkSettings"]["Networks"]["ceryx"]["IPAddress"]
    while not ipadress:
         ipadress = cli.inspect_container(container.id)['NetworkSettings']['Networks']['ceryx']['IPAddress']
    print(ipadress)
    ports = ['3000','80']
    for port in ports:
        data = {"source":str(container.id[:10])+"-"+str(port)+CONTAINER_HOST,"target":ipadress+':'+port}
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=CERYX_API_ENDPOINT, json=data, headers=headers)

    return container, ports










