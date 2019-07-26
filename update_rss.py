import datetime
import glob
import os
import pydub

import jinja2
from google.cloud import storage

storage_client = storage.Client.from_service_account_json("service_account.json")

bucket = storage_client.get_bucket("bestofhn")

items = [{
    'filename': os.path.basename(f),
    'size': os.stat(f).st_size,
    'duration': int(pydub.AudioSegment.from_mp3(f).duration_seconds),
    'date': datetime.datetime.strptime(os.path.basename(f)[9:19], "%Y-%m-%d").strftime("%c"),
    'nice_date': datetime.datetime.strptime(os.path.basename(f)[9:19], "%Y-%m-%d").strftime("%B %-d, %Y"),
} for f in reversed(sorted(glob.glob("podcasts/bestofhn_*.mp3")))]

item_template = jinja2.FileSystemLoader("templates").load(jinja2.Environment(), "podcast.rss")

output = item_template.render(items=items)

print(output)
blob = bucket.blob('bestofhn.rss')
blob.upload_from_string(output)
