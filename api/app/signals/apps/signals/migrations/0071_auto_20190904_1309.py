# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2019 - 2021 Gemeente Amsterdam
# Generated by Django 2.1.11 on 2019-09-04 11:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0070_sig-1525'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='storedsignalfilter',
            unique_together=set(),
        ),
    ]
