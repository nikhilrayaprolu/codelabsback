# Generated by Django 2.2.5 on 2019-10-26 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0022_auto_20191026_0907'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='uploaded_colab_file_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='track',
            name='container',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
