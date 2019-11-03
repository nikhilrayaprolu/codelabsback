import datetime
import io

import os
import re
import shutil
import time
from wsgiref.util import FileWrapper

import docker
from django.forms import model_to_dict
from django.http import HttpResponse
from docker import APIClient
import requests

import random
import string

from asgiref.sync import async_to_sync
from django.db import transaction
from gdown import download
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from pylti.common import generate_request_xml, LTIPostMessageException, _post_patched_request, post_message
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
# Create your views here.
from rest_framework_simplejwt.authentication import JWTAuthentication

from labs.forms import UploadFileForm
from labs.models import Track, Challenge, ContainerData, SubmittedAssignments
from labs.tasks import build_image
from .serializers import TopicSerializer, TrackSerializer, ChallengeSerializer, TopicTrackMappingSerializer, \
    TrackChallengeMappingSerializer, ContainerDataSerializer, SubmittedAssignmentsSerializer

client = docker.from_env()
cli = APIClient()
CERYX_API_ENDPOINT = settings.CERYX_API_ENDPOINT
CONTAINER_HOST = settings.CONTAINER_HOST
SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), 'newagent-958c5-2c6145f9840b.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)


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


class PublicTrackslist(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_public_tracks(self, user):
        return Track.objects.filter(public=True)

    def get(self, request):
        user = request.user
        public_tracks = self.get_public_tracks(user)
        public_tracks_serializer = TrackSerializer(public_tracks, many=True)
        return Response({'public_tracks': public_tracks_serializer.data}, status=200)


class Gettrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id=id)

    def get_challenges_by_track(self, track):
        return Challenge.objects.filter(track=track).order_by('challenge_position')

    def get(self, request, trackid):
        track = self.get_track_by_id(trackid)
        track_serializer = TrackSerializer(track)
        challenges = self.get_challenges_by_track(trackid)
        challenge_serializer = ChallengeSerializer(challenges, many=True)
        return Response({'track': track_serializer.data, 'challenges': challenge_serializer.data}, status=200)

    def put(self, request, trackid):
        new_track = request.data
        track = self.get_track_by_id(trackid)
        track_serializer = TrackSerializer(track, data=new_track, context={'request': request})
        if track_serializer.is_valid():
            track_serializer.save()
            return Response({'track': track_serializer.data}, status=200)
        else:
            print(track_serializer.errors)
            return Response(track_serializer.errors, status=500)

    def delete(self, request, trackid):
        track = self.get_track_by_id(trackid)
        track.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Copytrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id=id)

    def get_challenges_by_track(self, track):
        return Challenge.objects.filter(track=track).order_by('challenge_position')

    def get(self, request, trackid):
        track = self.get_track_by_id(trackid)
        previous_track_id = track.id
        track.pk = None
        track.id = None
        track.created_at = None
        track.updated_at = None
        track.user_created = None
        print(track.scenario_data)
        track.public = False
        track_dict = model_to_dict(track)
        print(track_dict)
        track_serializer = TrackSerializer(data=track_dict, context={'request': request})
        if track_serializer.is_valid():
            track_serializer.save()
            current_track_id = track_serializer.data['id']
            challenges = self.get_challenges_by_track(trackid)

            for challenge in challenges:
                challenge.pk = None
                challenge.id = None
                challenge.user_created = None
                challenge.created_at = None
                challenge.updated_at = None
                challenge.track_id = track_serializer.data['id']
                challenge_dict = model_to_dict(challenge)
                challenge_serializer = ChallengeSerializer(data=challenge_dict, context={'request': request})
                if challenge_serializer.is_valid():
                    challenge_serializer.save()
                else:
                    print(challenge_serializer.errors)
                    return Response({'error': challenge_serializer.errors}, status=500)
            current_volume_path = os.path.join(os.getcwd(), 'public', str(current_track_id), 'instructor', 'instructor')
            if not os.path.exists(current_volume_path):
                volume = os.makedirs(current_volume_path, exist_ok=True)
            previous_volume = os.path.join(os.getcwd(), 'public', str(previous_track_id), 'instructor', 'instructor')
            if previous_volume:
                copy_tree(previous_volume, current_volume_path)
            return Response({'success': True, 'trackid': track_serializer.data['id']}, status=200)
        else:
            print(track_serializer.errors)
            return Response({'error': track_serializer.errors}, status=500)


class GetChallenge(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_challenge_by_id(self, id):
        return Challenge.objects.get(id=id)

    def get(self, request, challengeid):
        challenge = self.get_challenge_by_id(challengeid)
        challenge_serializer = ChallengeSerializer(challenge)
        return Response({'challenge': challenge_serializer.data}, status=200)

    def put(self, request, challengeid):
        new_challenge = request.data
        challenge = self.get_challenge_by_id(challengeid)
        challenge_serializer = ChallengeSerializer(challenge, data=new_challenge, context={'request': request})
        if challenge_serializer.is_valid():
            challenge_serializer.save()
            return Response({'challenge': challenge_serializer.data}, status=200)
        else:
            print(challenge_serializer.errors)
            return Response(challenge_serializer.errors, status=500)

    def post(self, request):
        new_challenge = request.data
        challenge_serializer = ChallengeSerializer(data=new_challenge, context={'request': request})
        if challenge_serializer.is_valid():
            challenge_serializer.save()
            return Response({'challenge': challenge_serializer.data}, status=200)
        else:
            print(challenge_serializer.errors)
            return Response(challenge_serializer.errors, status=500)

    def delete(self, request, challengeid):
        challenge = self.get_challenge_by_id(challengeid)
        challenge.delete()
        return Response({'sucess': True}, status=status.HTTP_204_NO_CONTENT)


class RunTrack(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_track_by_id(self, id):
        return Track.objects.get(id=id)

    def get_challenges_by_track(self, track):
        return Challenge.objects.filter(track=track).order_by('challenge_position')

    def get_container_if_exists(self, trackid, courseid, studentid):
        try:
            print(trackid, courseid, studentid)
            container_data = ContainerData.objects.get(track_id=trackid, course_id=courseid, student_id=studentid)
            container_data_serialized = ContainerDataSerializer(container_data).data
        except ContainerData.DoesNotExist:
            container_data = None
            container_data_serialized = None
        return container_data_serialized

    def check_if_lab_submitted(self, trackid, courseid, studentid):
        try:
            return SubmittedAssignments.objects.get(track_id=trackid, course_id=courseid,
                                                    student_id=studentid).submit_status
        except SubmittedAssignments.DoesNotExist:
            return False
    def get_track_details(self, trackid):
        try:
            return Track.objects.get(id=trackid)
        except Track.DoesNotExist:
            return None

    def get(self, request, trackid, courseid=None, studentid=None):
        temp = False
        submitted = False
        if not courseid:
            courseid = randomString(5)
            temp = True
        if (courseid == "instructor") and not studentid:
            studentid = 'instructor'
        if not studentid:
            studentid = randomString(5)
            temp = True
        print(temp)
        container_data = None
        instructor_view = request.query_params.get('instructor', None)
        if instructor_view:
            studentid = 'inst-'+studentid
            temp = True

        if trackid and courseid and studentid:
            container_data = self.get_container_if_exists(trackid, courseid, studentid)
            print(container_data)
            print("yes container exists")
            if self.check_if_lab_submitted(trackid, courseid, studentid) == 'submitted':
                submitted = True
                print("yes submitted")
            else:
                submitted = False
        track_details = self.get_track_details(trackid)
        if not container_data:
            if track_details.labtype == 'colab':
                container_data = self.run_lab_from_colab_id(trackid, courseid, studentid, track_details.uploaded_colab_file_id, temp)
            else:
                container_data = run_image_from_track_id(trackid, courseid, studentid, temp, instructor_view)
            print("from second line", container_data)
        track = self.get_track_by_id(trackid)
        challenges = self.get_challenges_by_track(trackid)
        track_serializer = TrackSerializer(track)
        challenge_serializer = ChallengeSerializer(challenges, many=True)
        return Response(
            {'track': track_serializer.data, 'challenges': challenge_serializer.data, 'container_data': container_data,
             'submitted': submitted}, status=200)

    def run_lab_from_colab_id(self, trackid, courseid, studentid, parent_colab_file_id, temp):
        copied_file = {'title': 'practice.ipynb'}
        print(parent_colab_file_id)
        copy_file = service.files().copy(fileId=parent_colab_file_id, supportsAllDrives=True, supportsTeamDrives=True,
                                         fields='*', body=copied_file)
        copy_file = copy_file.execute()
        print(copy_file)
        print('File ID: %s' % copy_file.get('id'))
        container_run_by_instructor = False
        webview = copy_file.get('webViewLink') or copy_file.get('webContentLink')
        new_permission = {
            'type': 'anyone',
            'role': 'writer'
        }
        service.permissions().create(
                fileId = copy_file.get('id'), body=new_permission).execute()

        container_data = {
            'course_id': courseid,
            'student_id': studentid,
            'track_id': trackid,
            'submit_status': 'no',
            'container_run_by_instructor': container_run_by_instructor,
            'container_colab_file': copy_file.get('id'),
            'container_colab_webview': webview,
        }
        if temp:
            container_data['container_temp'] = True
        else:
            container_data['container_temp'] = False

        container_data_serializer = ContainerDataSerializer(data=container_data)
        if container_data_serializer.is_valid():
            container_data_serializer.save()
        else:
            print(container_data_serializer.errors)
        return container_data_serializer.data


class SubmitLab(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get_container_data(self, trackid, courseid, studentid):
        try:
            container_data = ContainerData.objects.get(track_id=trackid, course_id=courseid, student_id=studentid)
        except ContainerData.DoesNotExist:
            container_data = None
        return container_data

    def download_colab_locally(self, colabid, trackid, courseid, studentid):

        request = service.files().get_media(fileId=colabid)
        outputfolder = os.path.join(os.getcwd(), 'public', str(trackid), courseid, studentid)
        file_location = os.path.join(outputfolder, 'practice.ipynb')
        if not os.path.exists(outputfolder):
            volume = os.makedirs(outputfolder, exist_ok=True)
        fh = io.FileIO(file_location, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

    def get(self, request, trackid, courseid, studentid):
        data = {
            'track_id': trackid,
            'course_id': courseid,
            'student_id': studentid,
            'submit_status': "submitted"
        }
        submitted_assignemnt = get_submitted_assignment_if_exists(data)
        container_data = self.get_container_data(trackid, courseid, studentid)
        if container_data and container_data.container_colab_file:
            self.download_colab_locally(container_data.container_colab_file, trackid, courseid, studentid)
        if submitted_assignemnt:
            submitted_assignments_serializer = SubmittedAssignmentsSerializer(submitted_assignemnt, data=data, partial=True)
        else:
            submitted_assignments_serializer = SubmittedAssignmentsSerializer(data=data)
        if submitted_assignments_serializer.is_valid():
            submitted_assignments_serializer.save()
            return Response({'submitted': True}, status=200)
        else:
            print(submitted_assignments_serializer.errors)
            return Response({'error': submitted_assignments_serializer.errors}, status=500)

        # submitted_assignment_serializer = SubmittedAssignmentsSerializer(data = data)
        # if submitted_assignment_serializer.is_valid():
        #     submitted_assignment_serializer.save()


class SnapShotContainer(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, containerid, trackid):
        container = client.containers.get(containerid)
        container.commit(repository='nikhilrayaprolu/build_' + str(trackid), tag='latest')
        cli.push("nikhilrayaprolu/build_" + str(trackid), stream=True, decode=True)
        return Response({'success': True}, status=200)


class NewLab(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        track = request.data
        # print(newlab)
        # newlab['time_limit'] = str(newlab['timelimit']['hour']) + ':' + str(newlab['timelimit']['minute'])
        # print(newlab)
        # new_topic_serializer = TopicSerializer(data=newlab, context={'request': request})
        # if new_topic_serializer.is_valid():
        #     new_topic = new_topic_serializer.save()
        #     for track in newlab['tracks']:
        #         track['topic'] = new_topic.id

        new_track_serializer = TrackSerializer(data=track, context={'request': request})
        if new_track_serializer.is_valid():
            new_track = new_track_serializer.save(user_created=self.request.user)
            if new_track.labtype == 'colab':

                downloadid = re.search('[-\w]{25,}', new_track.colablink).group()
                # if in future copy doesn't work do this
                # url = 'https://drive.google.com/uc?id={id}'.format(id=downloadid)
                # outputfolder = os.path.join(os.getcwd(), 'public', str(new_track.id), 'instructor', 'instructor')
                # file_location = os.path.join(outputfolder, 'practice.ipynb')
                # if not os.path.exists(outputfolder):
                #     volume = os.makedirs(outputfolder, exist_ok=True)
                #
                # output = download(url=url, output=file_location, quiet=False)
                # print(output)
                # file_metadata = {'name': 'practice.ipynb'}
                # media = MediaFileUpload(file_location,
                #                         mimetype='application/vnd.google.colaboratory')
                # file = service.files().create(body=file_metadata,
                #                                     media_body=media,
                #                                     fields='id').execute()
                # print(file)
                # print('File ID: %s' % file.get('id'))
                # new_file_id = file.get('id')

                copy_file = service.files().copy(fileId=downloadid, supportsAllDrives=True, supportsTeamDrives=True).execute()
                print(copy_file)
                print('File ID: %s' % copy_file.get('id'))
                new_track_model = Track.objects.get(id=new_track.id)
                print(new_track_model)
                updated_track_serializer = TrackSerializer(new_track_model, data={'uploaded_colab_file_id': copy_file.get('id')}, partial=True)
                if updated_track_serializer.is_valid():
                    print('working')
                    updated_track = updated_track_serializer.save()
                    print(updated_track)
                else:
                    print(updated_track_serializer.errors)
                    return Response({'error': updated_track_serializer.errors}, status=500)


            print(new_track, "check")
            for challenge in track['challenges']:
                challenge['track'] = new_track.id
                new_challenge_serializer = ChallengeSerializer(data=challenge, context={'request': request})
                if new_challenge_serializer.is_valid():
                    new_challenge = new_challenge_serializer.save(user_created=self.request.user)
                    print(new_challenge)
                else:
                    print(new_challenge_serializer.errors)
                    return Response({'error': new_challenge_serializer.errors}, status=500)
            # image, build_output = build_image(track['container'], track['installscript'])
        else:
            print(new_track_serializer.errors)
            return Response({'error': new_track_serializer.errors}, status=500)
        # else:
        #     print(new_topic_serializer.errors)
        #     return Response({'error': new_topic_serializer.errors}, status=500)
        return Response({'success': True}, status=200)


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
            container_serializer = ContainerDataSerializer(container,
                                                           data={'container_last_ping_time': datetime.datetime.now()})
            if container_serializer.is_valid():
                container_serializer.save()
                return Response({'sucess': True, 'container_exists': True}, status=200)
            else:
                print(container_serializer.errors)
                return Response(container_serializer.errors, status=500)
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


def get_submitted_assignment_if_exists(data):
    try:
        submittedassignment = SubmittedAssignments.objects.get(track_id=data['track_id'], course_id=data['course_id'],
                                                               student_id=data['student_id'])
    except SubmittedAssignments.DoesNotExist:
        submittedassignment = None
    return submittedassignment


from distutils.dir_util import copy_tree


def run_image_from_track_id(trackid, courseid=None, studentid=None, temp=False, instructor_view=False):
    if not instructor_view:
        volume_path = os.path.join(os.getcwd(), 'public', str(trackid), str(courseid), str(studentid))
        if not os.path.exists(volume_path):
            volume = os.makedirs(volume_path, exist_ok=True)
            instructor_volume = os.path.join(os.getcwd(), 'public', str(trackid), 'instructor', 'instructor')
            if os.path.isdir(instructor_volume) and not (studentid == "instructor") and not (courseid == "instructor"):
                copy_tree(instructor_volume, volume_path)
        container_run_by_instructor = False
    else:
        volume_path = os.path.join(os.getcwd(), 'public', str(trackid), str(courseid), 'inst-'+str(studentid))
        if not os.path.exists(volume_path):
            volume = os.makedirs(volume_path, exist_ok=True)
        student_volume = os.path.join(os.getcwd(), 'public', str(trackid), str(courseid), str(studentid))
        if student_volume and not (studentid == "instructor") and not (courseid == "instructor"):
            copy_tree(student_volume, volume_path)
        container_run_by_instructor = True

    track = Track.objects.get(id=trackid)
    run_command = ''
    print(run_command)
    iframe = False
    if(track.scenario == 'iframe-editor'):
        iframe = True
        run_command = "\"" + track.configscript + "\""
    else:
        run_command = "sh -c \"" + track.configscript + "\""
    container, ports = run_lab(track.final_image, run_command, volume_path, str(trackid), str(courseid), str(studentid),
                               track.scenario_data['port'].split(","), iframe)
    container_data = {
        'container_id': container.id,
        'course_id': courseid,
        'student_id': studentid,
        'track_id': trackid,
        'container_ports': ports,
        'submit_status': 'no',
        'container_run_by_instructor': container_run_by_instructor
    }
    print(temp)
    if temp:
        container_data['container_temp'] = True
    else:
        container_data['container_temp'] = False

    container_data_serializer = ContainerDataSerializer(data=container_data)
    if container_data_serializer.is_valid():
        container_data_serializer.save()
    else:
        print(container_data_serializer.errors)

    submitted_assignemnt = get_submitted_assignment_if_exists(container_data)
    if submitted_assignemnt:
        submitted_assignments_serializer = SubmittedAssignmentsSerializer(submitted_assignemnt, data=container_data)
    else:
        submitted_assignments_serializer = SubmittedAssignmentsSerializer(data=container_data)
    if submitted_assignments_serializer.is_valid():
        submitted_assignments_serializer.save()
    else:
        print(submitted_assignments_serializer.errors)

    return container_data


def run_lab(image, run_command, volume, trackid, courseid, studentid, ports=[], iframe=False):
    print("I am up here dude too!")
    if iframe:
        container = client.containers.run(image, run_command, detach=True, network="ceryx",entrypoint=["/bin/bash", "-c"],
                                      volumes={volume: {'bind': '/home/project', 'mode': 'rw'}})
    else:
        print(image)
        print(volume)
        container = client.containers.run(image, run_command, detach=True, network="ceryx",
                                          volumes={volume: {'bind': '/wide_node/project', 'mode': 'rw'}})

    print("I am up here dude")
    ipaddress = vars(container)["attrs"]["NetworkSettings"]["Networks"]["ceryx"]["IPAddress"]
    while not ipaddress:
        ipaddress = cli.inspect_container(container.id)['NetworkSettings']['Networks']['ceryx']['IPAddress']
    print(ipaddress)
    ports = ['3000', '80'] + ports
    for port in ports:
        data = {"source": str(container.id[:10]) + "-" + str(port) + CONTAINER_HOST, "target": ipaddress + ':' + port}
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=CERYX_API_ENDPOINT, json=data, headers=headers)
        print(r.content, r.status_code)
    return container, ports


class SubmissionsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, submissionid):
        user = request.user
        submitted_assignment = SubmittedAssignments.objects.filter(id=submission_id)
        submitted_assignment_serializer = SubmittedAssignmentsSerializer(submitted_assignment)
        return Response({'submitted_assignment': submitted_assignment_serializer.data}, status=200)

class SubmissionsGrader(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, submissionid, grade):
        user = request.user
        submitted_assignment = SubmittedAssignments.objects.get(id=submissionid)
        lis_result_sourcedid = submitted_assignment.lis_result_sourcedid
        if lis_result_sourcedid:
            xml = generate_request_xml('{:.0f}'.format(time.time()), 'replaceResult', lis_result_sourcedid, grade)
            config = getattr(settings, 'PYLTI_CONFIG', dict())
            consumers = config.get('consumers', dict())
            print(consumers)
            print(submitted_assignment.consumer_key)
            if not post_message(
                consumers, submitted_assignment.consumer_key,
                    submitted_assignment.lis_outcome_service_url, xml):

                # Something went wrong, display an error.
                # Is 500 the right thing to do here?
                print("Scoring not successful")
            else:
                print('Your score was submitted. Great job!')

        submitted_assignment_serializer = SubmittedAssignmentsSerializer(submitted_assignment, data={'grade': grade, 'graded': True}, partial = True)
        if submitted_assignment_serializer.is_valid():
            submitted_assignment_serializer.save()
        else:
            return Response({'error': submitted_assignment_serializer.errors}, status=500)
        return Response({'submitted_assignment': submitted_assignment_serializer.data}, status=200)

class EvaluatorStats(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        print("came here")
        list_of_courses = SubmittedAssignments.objects.filter(track_id__user_created=request.user, container_temp=False).values_list(
            'course_id', flat=True).distinct()
        course_count = len(list_of_courses)
        student_count = SubmittedAssignments.objects.filter(track_id__user_created=request.user,
                                                            container_temp=False).count()
        temporary_containers = SubmittedAssignments.objects.filter(track_id__user_created=request.user,
                                                                   container_temp=True).count()
        return Response({'course_count': course_count, 'list_of_courses': list_of_courses, 'student_count': student_count,
                  'temporary_containers': temporary_containers}, status=200)


class EvaluatorCourseStats(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, courseid):
        user = request.user
        list_of_tracks = Track.objects.filter(submittedassignments__course_id=courseid, user_created=user).distinct()
        number_of_tracks = len(list_of_tracks)
        tracks_serializer = TrackSerializer(list_of_tracks, many=True)
        return Response({'list_of_tracks': tracks_serializer.data, 'number_of_tracks': number_of_tracks}, status=200)


class EvaluatorTrackCourseStats(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, courseid, trackid):
        user = request.user
        list_of_submissions = SubmittedAssignments.objects.filter(track_id=trackid, course_id=courseid,
                                                                  submit_status="submitted")
        total_number_of_students = SubmittedAssignments.objects.filter(track_id=trackid, course_id=courseid).count()
        total_number_of_submissions = len(list_of_submissions)
        submissions_serializer = SubmittedAssignmentsSerializer(list_of_submissions, many=True)
        return Response({'list_of_submissions': submissions_serializer.data,
                  'total_number_of_students': total_number_of_students,
                  'total_number_of_submissions': total_number_of_submissions}, status=200)


class StartIframe(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_container_if_exists(self, containerid):
        try:
            container_data = ContainerData.objects.get(container_id=containerid)
            container_data_serialized = ContainerDataSerializer(container_data).data
        except ContainerData.DoesNotExist:
            container_data_serialized = None
        return container_data_serialized

    def get(self, request, containerid, port):
        ipaddress = None
        while not ipaddress:
            ipaddress = cli.inspect_container(containerid)['NetworkSettings']['Networks']['ceryx']['IPAddress']
        data = {"source": str(containerid[:10]) + "-" + str(port) + CONTAINER_HOST, "target": ipaddress + ':' + str(port)}
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=CERYX_API_ENDPOINT, json=data, headers=headers)
        container_data = self.get_container_if_exists(containerid)
        if container_data:
            container_data_serializer = ContainerDataSerializer(data=container_data)
            if container_data_serializer.is_valid():
                container_data_serializer.save()
            else:
                Response({'error': container_data_serializer.errors}, status=500)
        else:
            Response({'error': 'container doesn\'t exist'}, status=500)

        return Response({'success': True}, status=200)


import zipfile


class FileUploadView(APIView):
    parser_classes = (FileUploadParser,)

    def post(self, request, trackid, filename, courseid=None, studentid=None):
        up_file = request.data['file']
        if courseid and studentid:
            volume_path = os.path.join(os.getcwd(), 'public', str(trackid), courseid, studentid)
            print(volume_path)
        if os.path.exists(volume_path):
            for the_file in os.listdir(volume_path):
                file_path = os.path.join(volume_path, the_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except Exception as e:
                    print(e)
            # shutil.rmtree(volume_path)
        volume = os.makedirs(volume_path, exist_ok=True)
        file_destination = os.path.join(volume_path, filename)
        print(file_destination)
        destination = open(file_destination, 'wb+')
        for chunk in up_file.chunks():
            destination.write(chunk)
        destination.close()
        if (zipfile.is_zipfile(file_destination)):
            with zipfile.ZipFile(file_destination, 'r') as zip_ref:
                zip_ref.extractall(volume_path)
        print(file_destination)
        os.remove(file_destination)
        return Response({'sucess': True}, status.HTTP_201_CREATED)

    def delete(self, request, trackid):
        volume_path = os.path.join(os.getcwd(), 'public', str(trackid), "instructor", "instructor")
        shutil.rmtree(volume_path)
        volume = os.makedirs(volume_path, exist_ok=True)

        return Response({'sucess': True}, status.HTTP_204_NO_CONTENT)

class FileDownload(APIView):
    def get(self, request, trackid, courseid, studentid):
        print(os.getcwd())
        volume_path = os.path.join(os.getcwd(), 'public', str(trackid), courseid, studentid)
        compressed_path = os.path.join(os.getcwd(), 'public2', str(trackid), courseid, studentid)
        temporary_zip_location = os.path.join(compressed_path, 'temporary.zip')
        temporary_zip_name = os.path.join(compressed_path, 'temporary')
        if os.path.exists(temporary_zip_location):
            os.remove(temporary_zip_location)
        volume = os.makedirs(compressed_path, exist_ok=True)
        shutil.make_archive(temporary_zip_name, 'zip', volume_path)
        url = os.path.join('media', str(trackid), courseid, studentid, 'temporary.zip')
        return Response({'sucess': True, 'url': url}, 200)


class ResetFolder(APIView):
    def get(self, request, trackid, courseid, studentid):
        reset_path = os.path.join(os.getcwd(), 'public', str(trackid), str(courseid), str(studentid))
        instructor_volume = os.path.join(os.getcwd(), 'public', str(trackid), 'instructor', 'instructor')
        if os.path.exists(instructor_volume):
            # if os.path.exists(reset_path):
            #     shutil.rmtree(reset_path)
            os.makedirs(reset_path, exist_ok=True)
            copy_tree(instructor_volume, reset_path)
            return Response({'sucess': True}, 200)
        return Response({'sucess': False, 'error': "No instructor volume"}, 400)

