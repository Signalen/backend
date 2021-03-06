# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2018 - 2021 Gemeente Amsterdam
# Generated by Django 2.1.7 on 2019-03-25 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0040_auto_20190321_1226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='status',
            name='state',
            field=models.CharField(blank=True, choices=[
                ('m', 'Gemeld'),
                ('i', 'In afwachting van behandeling'),
                ('b', 'In behandeling'),
                ('h', 'On hold'),
                ('ready to send', 'Te verzenden naar extern systeem'),
                ('o', 'Afgehandeld'),
                ('a', 'Geannuleerd'),
                ('reopened', 'Heropend'),
                ('s', 'Gesplitst'),
                ('closure requested', 'Verzoek tot afhandeling'),
                ('sent', 'Verzonden naar extern systeem'),
                ('send failed', 'Verzending naar extern systeem mislukt'),
                ('done external', 'Melding is afgehandeld in extern systeem')
            ], default='m', help_text='Melding status', max_length=20),
        ),
    ]
