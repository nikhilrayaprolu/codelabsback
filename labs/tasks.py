import os
import shutil
import tempfile
from datetime import timedelta

from django.utils import timezone

import channels
import requests
from asgiref.sync import async_to_sync
from celery.schedules import crontab
from celery.task import task, periodic_task
from django.conf import settings
from docker import APIClient

from labs.models import ContainerData

import docker

client = docker.from_env()
cli = APIClient()
CERYX_API_ENDPOINT = settings.CERYX_API_ENDPOINT
CONTAINER_HOST = settings.CONTAINER_HOST

@task(name="build_image")
def build_image(container_name, installation_script, trackid):
    command1 = 'FROM ' + container_name + '\n' + 'COPY installation_script.sh installation_script.sh\n RUN chmod 700 ./installation_script.sh \n RUN cat ./installation_script.sh \n RUN /bin/bash ./installation_script.sh\n'
    dirpath = tempfile.mkdtemp()
    print(dirpath)
    installation_file = open(dirpath + "/installation_script.sh", "w+", newline='\n')
    installation_script = installation_script.replace('\r\n', '\n')
    print(print(repr(installation_script)))
    installation_file.write(installation_script)
    installation_file.close()

    docker_file = open(dirpath + "/Dockerfile", "w+", newline='\n')
    docker_file.write(command1)
    docker_file.close()
    os.listdir(dirpath)
    try:
        for line in cli.build(path=dirpath, rm=True, nocache=True, decode=True, tag="nikhilrayaprolu/build_"+str(trackid)):
            # Send message to room group
            channel_layer = channels.layers.get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'build_'+str(trackid),
                    {
                        'type': 'build_message',
                        'message': line
                    }
                )
            print(line)
        for line in cli.push("nikhilrayaprolu/build_"+str(trackid), stream=True, decode=True):
            channel_layer = channels.layers.get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'build_' + str(trackid),
                {
                    'type': 'build_message',
                    'message': line
                }
            )
            print(line)


        #image, generator = client.images.build(path=dirpath, nocache=True)
    except docker.errors.BuildError as e:
        print(e.msg)
        for line in e.build_log:
            print(line)



def get_containers_idle(idletime=None):
    if idletime:
        time_threshold = timezone.now() - timedelta(minutes=idletime)
        return ContainerData.objects.filter(container_last_ping_time__lt=time_threshold)
    else:
        return  ContainerData.objects.filter()


def remove_idle_containers():
    containers_data = get_containers_idle(60)
    for container_data in containers_data:
        try:
            container = client.containers.get(container_data.container_id)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        if container_data.container_temp:
            container_volume_dir = os.path.join(os.getcwd(),'public', str(container_data.track_id_id), str(container_data.course_id), str(container_data.student_id))
            print(container_volume_dir)
            try:
                shutil.rmtree(container_volume_dir)
            except FileNotFoundError as e:
                print(e)
        print(container_data.container_ports)
        container_ports = list(container_data.container_ports)

        for port in container_ports:
            delete_endpoint = str(container_data.container_id[:10]) + "-" + str(port) + CONTAINER_HOST
            print(delete_endpoint)
            headers = {'Content-type': 'application/json'}
            r = requests.delete(url=CERYX_API_ENDPOINT+delete_endpoint, headers=headers)
            print(r)
            print(r.text)
    containers_data.delete()


@periodic_task(run_every=(crontab(minute='*/10')), name="remove_idle_containers", ignore_result=True)
def remove_idle_containers_task():
    remove_idle_containers()





