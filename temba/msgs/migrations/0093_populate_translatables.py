# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-01 13:56
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import time

from django.db import migrations
from temba.utils import chunk_list


def populate_translatables(Org, Broadcast):
    broadcast_ids = list(Broadcast.objects.filter(translations=None).values_list('id', flat=True))
    if not broadcast_ids:
        return

    print("Fetched %d broadcast ids to be updated..." % len(broadcast_ids))

    primary_lang_by_org_id = {}
    for org in Org.objects.select_related('primary_language'):
        primary_lang_by_org_id[org.id] = org.primary_language.iso_code if org.primary_language else None

    print("Fetched %d org primary languages..." % (len(primary_lang_by_org_id)))

    num_updated = 0
    start = time.time()

    for id_batch in chunk_list(broadcast_ids, 5000):
        batch = Broadcast.objects.filter(id__in=id_batch)
        for broadcast in batch:
            org_language = primary_lang_by_org_id[broadcast.org_id]

            # Figure out base language for this broadcast
            if broadcast.base_language:
                base_language = broadcast.base_language
            elif org_language:
                base_language = org_language
            else:
                base_language = 'base'

            translations = json.loads(broadcast.language_dict) if broadcast.language_dict else None

            # We might have a valid translations dict, an empty dict or none
            if translations:
                # We have some broadcasts with language dicts with language keys other than anything calculated above.
                # In this case best we can do is a pick a random key so at least base_language exists in language_dict
                if base_language not in translations:
                    base_language = next(iter(translations.keys()))
            else:
                translations = {base_language: broadcast.text}

            if broadcast.media_dict:
                media = json.loads(broadcast.media_dict)
            else:
                media = None

            broadcast.translations = translations
            broadcast.media = media
            broadcast.base_language = base_language
            broadcast.save(update_fields=('translations', 'media', 'base_language'))

        num_updated += len(batch)
        time_taken = time.time() - start
        completion = float(num_updated) / len(broadcast_ids)
        total_time = time_taken / completion
        time_remaining = total_time - time_taken

        print("> Updated %d of %d broadcasts (est. time remaining: %d minutes)"
              % (num_updated, len(broadcast_ids), int(time_remaining / 60)))


def apply_manual():
    from temba.msgs.models import Broadcast
    from temba.orgs.models import Org
    populate_translatables(Org, Broadcast)


def apply_as_migration(apps, schema_editor):
    Broadcast = apps.get_model('msgs', 'Broadcast')
    Org = apps.get_model('orgs', 'Org')
    populate_translatables(Org, Broadcast)


class Migration(migrations.Migration):

    dependencies = [
        ('msgs', '0092_auto_20170428_1935'),
    ]

    operations = [
        migrations.RunPython(apply_as_migration)
    ]
