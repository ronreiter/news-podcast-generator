from config import *
import http.client
import json
import storage
import datetime
import logging

def get_news_newscaf(cat="technology"):
    t = datetime.date.today()

    conn = http.client.HTTPSConnection(NEWSCAF_HOST)

    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': NEWSCAF_HOST
    }

    conn.request("GET", f"/apirapid/news/{cat}/", headers=headers)

    res = conn.getresponse()
    data = res.read()
    news = json.loads(data)

    binary = json.dumps(news, indent=True)
    fn = "newscaf_%s_%s.json" % (cat, t.isoformat())
    storage.upload_blob(BUCKET_NAME, fn, binary)

    return "https://%s.storage.googleapis.com/%s" % (BUCKET_NAME, fn)


def get_news_bing(cat="ScienceAndTechnology"):
    t = datetime.date.today()

    conn = http.client.HTTPSConnection(BING_HOST)

    headers = {
        'x-bingapis-sdk': "true",
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': BING_HOST
    }

    conn.request("GET", f"/news?count=100&mkt=en-US&safeSearch=Off&textFormat=Raw&originalImg=true&category={cat}", headers=headers)

    res = conn.getresponse()
    data = res.read()
    news = json.loads(data)

    binary = json.dumps(news, indent=True)
    fn = "news/bing_%s_%s.json" % (cat, t.isoformat())
    storage.upload_blob(BUCKET_NAME, fn, binary)

    return "https://%s.storage.googleapis.com/%s" % (BUCKET_NAME, fn)


def main(request):
    logging.info(request)
    return get_news_bing()