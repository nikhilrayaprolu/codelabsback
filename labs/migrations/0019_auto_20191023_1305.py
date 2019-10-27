# Generated by Django 2.2.5 on 2019-10-23 13:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0018_remove_track_no_challenges'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedassignments',
            name='container_temp',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='submittedassignments',
            name='track_id',
            field=models.ForeignKey(on_delete='CASCADE', related_name='submittedassignments', to='labs.Track'),
        ),
        migrations.AlterUniqueTogether(
            name='submittedassignments',
            unique_together={('track_id', 'course_id', 'student_id')},
        ),
    ]
