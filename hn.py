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
import storage

logging.basicConfig(level=logging.INFO)

from aylien import summarize
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from config import *

# constants
TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
TTS_URL_IBM = "https://gateway-wdc.watsonplatform.net/text-to-speech/api"
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

t = jinja2.FileSystemLoader(TEMPLATE_FOLDER)
authenticator = IAMAuthenticator(IBM_API_KEY)
text_to_speech = TextToSpeechV1(authenticator=authenticator)
text_to_speech.set_service_url(TTS_URL_IBM)


def ssml_to_audio_google(ssml, format='audio/ogg;codecs=opus', voice_type=VOICE_TYPE, voice_gender=VOICE_GENDER, voice_lang=VOICE_LANG):
    accept_to_format = {
        'audio/ogg;codecs=opus': 'OGG_OPUS',
        'audio/wav': 'LINEAR16',
        'audio/mp3': 'MP3'
    }

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
            'audioEncoding': accept_to_format[format]
        }
    }), headers={
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "Content-Type": "application/json"
    }).json()

    if 'audioContent' not in json_output:
        raise Exception(json_output['error']['message'])

    raw_data = codecs.decode(json_output['audioContent'].encode("utf-8"), "base64")

    return raw_data

def ssml_to_audio_ibm(ssml, format='audio/ogg;codecs=opus'):
    return text_to_speech.synthesize(ssml, voice='en-US_LisaV3Voice', accept=format).get_result().content


def get_best_hn_urls(num=10, news_date=None):
    if news_date:
        html_data = requests.get(STORIES_FOR_DATE_PAGE % news_date).content
        top_items = re.findall(b"<tr class='athing' id='(\d+)'>", html_data)
        top_items = [int(x) for x in top_items]
    else:
        top_items = requests.get(BEST_STORIES_API).json()

    links = []
    for item in top_items[:num]:
        cached = "story_cache/%s.json" % item
        if not os.path.exists(cached):
            logging.info('reading item %s', STORY_API % item)
            item_data = requests.get(STORY_API % item).json()
            open("story_cache/%s.json" % item, "w").write(json.dumps(item_data))
        else:
            item_data = json.load(open("story_cache/%s.json" % item))

        if 'url' in item_data:
            links.append(item_data['url'])

    return links


def get_news_data(urls):
    out = []

    for url in urls:
        general_data, summary_data = summarize(url)

        if not "title" in general_data:
            continue

        if not "sentences" in summary_data:
            continue

        out.append({
            "title": general_data['title'],
            "author": general_data['author'],
            "date": general_data['publishDate'],
            "article": general_data['article'],
            "image": general_data['image'],
            "sentences": summary_data['sentences'],
            "url": url,
        })

    return out

def single_file():
    news_template = t.load(jinja2.Environment(), "news.ssml")
    ssml = news_template.render(news_data=news_data)
    raw_data = ssml_to_audio(ssml)

    with open(fn, "wb") as f:
        f.write(raw_data)


def generate_podcast(news_items, news_date, podcast_fn):
    item_template = t.load(jinja2.Environment(), "item.ssml")

    items = []

    for item in news_items:
        logging.info('processing %s' % item['title'])
        item_ssml = item_template.render(item)
        item_hash = hashlib.md5(item_ssml.encode('utf8')).hexdigest()
        blob_name = os.path.join(TEMP_FOLDER, '%s.wav' % item_hash)

        if not os.path.exists(blob_name):
            raw_data = ssml_to_audio_ibm(item_ssml, format='audio/wav')
            # raw_data = ssml_to_audio(item_ssml, format='audio/wav')

            with open(blob_name, 'wb') as f:
                f.write(raw_data)

        logging.info('saved %s' % blob_name)
        items.append(blob_name)

    news_date_parsed = datetime.datetime.strptime(news_date, "%Y-%m-%d")
    intro_file = os.path.join(TEMP_FOLDER, "intro_%s.wav" % news_date)
    goodbye_file = os.path.join(TEMP_FOLDER, "goodbye.wav")

    if not os.path.exists(intro_file):
        open(intro_file, "wb").write(ssml_to_audio_google(t.load(jinja2.Environment(), "intro.ssml").render(news_date=news_date_parsed), format='audio/wav'))

    if not os.path.exists(goodbye_file):
        open(goodbye_file, "wb").write(ssml_to_audio_google(t.load(jinja2.Environment(), "goodbye.ssml").render(), format='audio/wav'))

    final = pydub.AudioSegment.empty()

    final += pydub.AudioSegment.from_mp3(intro_file)
    for item in items:
        final += pydub.AudioSegment.from_mp3('resources/Everythings_Nice_Sting.mp3')
        final += pydub.AudioSegment.from_wav(item)

    final += pydub.AudioSegment.from_mp3(goodbye_file)

    logging.info('saving %s' % podcast_fn)
    final.export(podcast_fn, format="mp3")

    logging.info('uploading...')
    storage.upload_file(BUCKET_NAME, podcast_fn, podcast_fn)


def generate_rss_feed():
    items = []
    for f in reversed(sorted(glob.glob(os.path.join(PODCASTS_FOLDER, "bestofhn_*.mp3")))):
        podcast_date = datetime.datetime.strptime(os.path.basename(f)[9:19], "%Y-%m-%d")
        items.append({
            'filename': f,
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
        generate_podcast(news_data, news_date, fn)

    rss_feed = generate_rss_feed()
    print(rss_feed)
    storage.upload_blob(BUCKET_NAME, 'bestofhn.rss', rss_feed)
