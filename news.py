from config import *
import http.client
import json
import storage
import datetime


def get_news_newscaf():
    t = datetime.date.today()

    conn = http.client.HTTPSConnection(NEWSCAF_HOST)

    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': NEWSCAF_HOST
    }

    conn.request("GET", "/apirapid/news/technology/", headers=headers)

    res = conn.getresponse()
    data = res.read()
    news = json.loads(data)

    binary = json.dumps(news, indent=True)

    storage.upload_blob(BUCKET_NAME, "newscaf_%s.json" % t.isoformat(), binary)


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

    storage.upload_blob(BUCKET_NAME, "news/bing_%s.json" % t.isoformat(), binary)
