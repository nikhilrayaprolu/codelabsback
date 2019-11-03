# Generated by Django 2.2.5 on 2019-10-30 15:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMiniProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='mini_user_profile', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('first_name', models.CharField(blank=True, max_length=100, null=True)),
                ('last_name', models.CharField(blank=True, max_length=100, null=True)),
                ('alloted_institute_code', models.CharField(blank=True, max_length=100, null=True)),
                ('gender', models.CharField(blank=True, max_length=1, null=True)),
                ('email', models.CharField(blank=True, max_length=40, null=True)),
                ('contact_number', models.CharField(blank=True, max_length=40, null=True)),
                ('is_staff', models.BooleanField(blank=True)),
            ],
        ),
    ]
