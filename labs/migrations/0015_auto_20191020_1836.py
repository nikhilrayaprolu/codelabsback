# Generated by Django 2.2.5 on 2019-10-20 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0014_track_public'),
    ]

    operations = [
        migrations.AlterField(
            model_name='challenge',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
