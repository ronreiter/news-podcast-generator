import codecs
import datetime
import hashlib
import json
import os
import pydub

import requests
import jinja2
import logging

logging.basicConfig(level=logging.INFO)

from aylienapiclient import textapi
from google.cloud import storage

from config import *

# https://developers.google.com/analytics/devguides/config/mgmt/v3/quickstart/service-py
# from apiclient.discovery import build
# from oauth2client.service_account import ServiceAccountCredentials
# credentials = ServiceAccountCredentials.from_json_keyfile_name("creds.json", 'https://texttospeech.googleapis.com/v1beta1/text:synthesize')
# service = build('texttospeech', 'v3', credentials)


# constants
TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
BEST_STORIES_API = "https://hacker-news.firebaseio.com/v0/beststories.json"
STORY_API = "https://hacker-news.firebaseio.com/v0/item/%s.json"
VOICE_TYPE = 'en-US-WaveNet-D'
VOICE_GENDER = 'MALE'
VOICE_LANG = 'en-us'
TOTAL_SENTENCES = 2
NUMBER_ARTICLES = 30
TEMPLATE_FOLDER = "templates"

storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_CREDS)

def upload_blob(bucket_name, blob_name, data):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)

def upload_file(bucket_name, blob_name, fn):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(fn)

def blob_exists(bucket_name, blob_name):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.exists()


def ssml_to_audio(ssml, format='OGG_OPUS', voice_type=VOICE_TYPE, voice_gender=VOICE_GENDER, voice_lang=VOICE_LANG):
    json_output = requests.post(TTS_URL, json.dumps({
        'input': {
            'ssml': ssml
        },
        'voice': {
            'languageCode': voice_lang,
            'name': voice_type,
            'ssmlGender': voice_gender
        },
        'audioConfig': {
            'audioEncoding': format
        }
    }), headers={
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "Content-Type": "application/json"
    }).json()

    if 'audioContent' not in json_output:
        raise Exception(json_output['error']['message'])

    raw_data = codecs.decode(json_output['audioContent'].encode("utf-8"), "base64")

    return raw_data

def get_best_hn_urls(num=10):
    top_items = requests.get(BEST_STORIES_API).json()
    links = []
    for item in top_items[:num]:
        item_data = requests.get(STORY_API % item).json()
        if 'url' in item_data:
            links.append(item_data['url'])

    return links

def get_news_data(urls):
    client = textapi.Client(AYLIEN_API_ID, AYLIEN_API_KEY)

    out = []

    for url in urls:
        general_data = client.Extract({'url': url})
        summary_data = client.Summarize({'url': url, 'sentences_number': TOTAL_SENTENCES})
        if not general_data['title']:
            continue

        if not summary_data['sentences']:
            continue

        out.append({
            "title": general_data['title'],
            "sentences": summary_data['sentences']
        })

    return out

def single_file():
    news_template = jinja2.FileSystemLoader(TEMPLATE_FOLDER).load(jinja2.Environment(), "news.ssml")
    ssml = news_template.render(news_data=news_data)
    raw_data = ssml_to_audio(ssml)

    with open(fn, "wb") as f:
        f.write(raw_data)


if __name__ == '__main__':
    today = datetime.date.today().isoformat()
    news_file = 'news_data/news_data_%s.json' % today

    logging.info('getting news data...')
    if not os.path.exists(news_file):
        news_data = get_news_data(get_best_hn_urls(NUMBER_ARTICLES))
        json.dump(news_data, open(news_file, "w"))
    else:
        news_data = json.load(open(news_file))

    item_template = jinja2.FileSystemLoader(TEMPLATE_FOLDER).load(jinja2.Environment(), "item.ssml")

    items = []

    for item in news_data:
        logging.info('processing %s' % item['title'])
        item_ssml = item_template.render(item)
        item_hash = hashlib.md5(item_ssml.encode('utf8')).hexdigest()
        blob_name = 'temp/%s.wav' % item_hash

        if not os.path.exists(blob_name):
            raw_data = ssml_to_audio(item_ssml, format='LINEAR16')
            with open(blob_name, 'wb') as f:
                f.write(raw_data)

        logging.info('saved %s' % blob_name)
        items.append(blob_name)

    final = pydub.AudioSegment.empty()

    final += pydub.AudioSegment.from_mp3('resources/main.mp3')
    for item in items:
        final += pydub.AudioSegment.from_mp3('resources/interim.mp3')
        final += pydub.AudioSegment.from_wav(item)

    final += pydub.AudioSegment.from_mp3('resources/main.mp3')

    fn = "bestofhn_%s.mp3" % today
    logging.info('saving %s' % fn)
    final.export(os.path.join('podcasts', fn), format="mp3")

    logging.info('uploading...')
    upload_file(BUCKET_NAME, fn, fn)

