# Generated by Django 2.2.5 on 2019-10-19 13:17

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0011_containerdata_container_temp'),
    ]

    operations = [
        migrations.AddField(
            model_name='containerdata',
            name='container_last_ping_time',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='containerdata',
            name='container_ports',
            field=jsonfield.fields.JSONField(default=dict),
        ),
    ]
