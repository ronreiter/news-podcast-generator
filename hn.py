import argparse
import codecs
import datetime
import glob
import hashlib
import json
import os
import re

import pydub

import requests
import jinja2
import logging

logging.basicConfig(level=logging.INFO)

from aylienapiclient import textapi
from google.cloud import storage

from config import *

# TODO: use the google API client library instead of sending an HTTP request
# https://developers.google.com/analytics/devguides/config/mgmt/v3/quickstart/service-py
# from apiclient.discovery import build
# from oauth2client.service_account import ServiceAccountCredentials
# credentials = ServiceAccountCredentials.from_json_keyfile_name("creds.json", 'https://texttospeech.googleapis.com/v1beta1/text:synthesize')
# service = build('texttospeech', 'v3', credentials)

# constants
TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
BEST_STORIES_API = "https://hacker-news.firebaseio.com/v0/beststories.json"
STORIES_FOR_DATE_PAGE = "https://news.ycombinator.com/front?day=%s"
STORY_API = "https://hacker-news.firebaseio.com/v0/item/%s.json"
VOICE_TYPE = 'en-US-WaveNet-D'
VOICE_GENDER = 'MALE'
VOICE_LANG = 'en-us'
TOTAL_SENTENCES = 2
NUMBER_ARTICLES = 30
TEMPLATE_FOLDER = "templates"
PODCASTS_FOLDER = "podcasts"
NEWS_DATA_FOLDER = "news_data"
TEMP_FOLDER = "temp"

storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_CREDS)
t = jinja2.FileSystemLoader(TEMPLATE_FOLDER)

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

def get_best_hn_urls(num=10, news_date=None):
    if news_date:
        html_data = requests.get(STORIES_FOR_DATE_PAGE % news_date).content
        top_items = re.findall(b"<tr class='athing' id='(\d+)'>", html_data)
        top_items = [int(x) for x in top_items]
    else:
        top_items = requests.get(BEST_STORIES_API).json()

    links = []
    for item in top_items[:num]:
        logging.info('reading item %s', STORY_API % item)
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
    news_template = t.load(jinja2.Environment(), "news.ssml")
    ssml = news_template.render(news_data=news_data)
    raw_data = ssml_to_audio(ssml)

    with open(fn, "wb") as f:
        f.write(raw_data)


def generate_podcast(news_items, podcast_fn):
    item_template = t.load(jinja2.Environment(), "item.ssml")

    items = []

    for item in news_items:
        logging.info('processing %s' % item['title'])
        item_ssml = item_template.render(item)
        item_hash = hashlib.md5(item_ssml.encode('utf8')).hexdigest()
        blob_name = os.path.join(TEMP_FOLDER, '%s.wav' % item_hash)

        if not os.path.exists(blob_name):
            raw_data = ssml_to_audio(item_ssml, format='LINEAR16')
            with open(blob_name, 'wb') as f:
                f.write(raw_data)

        logging.info('saved %s' % blob_name)
        items.append(blob_name)

    final = pydub.AudioSegment.empty()

    final += pydub.AudioSegment.from_mp3('resources/intro.wav')
    for item in items:
        final += pydub.AudioSegment.from_mp3('resources/Everythings_Nice_Sting.mp3')
        final += pydub.AudioSegment.from_wav(item)

    final += pydub.AudioSegment.from_mp3('resources/goodbye.wav')

    logging.info('saving %s' % podcast_fn)
    final.export(podcast_fn, format="mp3")

    logging.info('uploading...')
    upload_file(BUCKET_NAME, podcast_fn, podcast_fn)


def generate_rss_feed():
    items = []
    for f in reversed(sorted(glob.glob(os.path.join(PODCASTS_FOLDER, "bestofhn_*.mp3")))):
        podcast_date = datetime.datetime.strptime(os.path.basename(f)[9:19], "%Y-%m-%d")
        items.append({
            'filename': os.path.basename(f),
            'size': os.stat(f).st_size,
            'duration': int(pydub.AudioSegment.from_mp3(f).duration_seconds),
            'date': podcast_date.strftime("%c"),
            'nice_date': podcast_date.strftime("%B %-d, %Y"),
        })

    item_template = t.load(jinja2.Environment(), "podcast.rss")

    return item_template.render(items=items)


if __name__ == '__main__':
    # create directories
    for d in [PODCASTS_FOLDER, NEWS_DATA_FOLDER, TEMP_FOLDER]:
        if not os.path.exists(d):
            os.mkdir(d)

    # generate resources
    if not os.path.exists("resources/intro.wav"):
        open("resources/intro.wav", "wb").write(ssml_to_audio(t.load(jinja2.Environment(), "intro.ssml").render(), format='LINEAR16'))
    if not os.path.exists("resources/goodbye.wav"):
        open("resources/goodbye.wav", "wb").write(ssml_to_audio(t.load(jinja2.Environment(), "goodbye.ssml").render(), format='LINEAR16'))

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--date", default=(datetime.date.today() - datetime.timedelta(days=1)).isoformat())
    args = parser.parse_args()

    news_date = args.date
    news_file = os.path.join(NEWS_DATA_FOLDER, 'news_data_%s.json' % news_date)

    logging.info('getting news data...')
    if not os.path.exists(news_file):
        news_data = get_news_data(get_best_hn_urls(NUMBER_ARTICLES, news_date))
        json.dump(news_data, open(news_file, "w"))
    else:
        news_data = json.load(open(news_file))

    fn = os.path.join(PODCASTS_FOLDER, "bestofhn_%s.mp3" % news_date)

    if not os.path.exists(fn):
        generate_podcast(news_data, fn)

    rss_feed = generate_rss_feed()
    print(rss_feed)
    upload_blob(BUCKET_NAME, 'bestofhn.rss', rss_feed)
