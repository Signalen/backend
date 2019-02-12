# Generated by Django 2.1.5 on 2019-02-05 10:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('signals', '0031_auto_20190130_1531'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,
                                        verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.EmailField(blank=True, max_length=254, null=True)),
                ('file', models.FileField(max_length=255, upload_to='attachments/%Y/%m/%d/')),
                ('mimetype', models.CharField(max_length=30)),
                ('is_image', models.BooleanField(default=False)),
                ('_signal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              to='signals.Signal')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
