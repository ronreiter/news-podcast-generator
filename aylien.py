import hashlib

import storage
from config import *
import http.client
import json

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': AYLIEN_RAPIDAPI_HOST
}

def summarize(url):
    # open("cached_summaries/%s_extract.json" % hashlib.md5(url))

    conn = http.client.HTTPSConnection(AYLIEN_RAPIDAPI_HOST)
    conn.request("GET", f"/extract?url={url}", headers=headers)
    extract_data = json.loads(conn.getresponse().read().decode("utf-8"))

    conn.request("GET", f"/summarize?url={url}", headers=headers)
    summarize_data = json.loads(conn.getresponse().read().decode("utf-8"))

    return extract_data, summarize_data


def get_summary_for_url(url):
    fn = "summary/%s.json" % (hashlib.md5(url.encode('utf8')).hexdigest())
    if storage.blob_exists(BUCKET_NAME, fn):
        return storage.get_blob(BUCKET_NAME, fn)

    general_data, summary_data = summarize(url)

    if not "title" in general_data:
        return

    if not "sentences" in summary_data:
        return

    data = {
        "title": general_data['title'],
        "author": general_data['author'],
        "date": general_data['publishDate'],
        "article": general_data['article'],
        "image": general_data['image'],
        "sentences": summary_data['sentences'],
        "url": url,
    }

    binary = json.dumps(data, indent=True)
    storage.upload_blob(BUCKET_NAME, fn, binary)

    return binary

def get_summary_for_url_entrypoint(request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }

        return ('', 204, headers)

    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    return (get_summary_for_url(request.args['url']), 200, headers)

def get_news_data(urls):
    out = []

    for url in urls:
        data = get_summary_for_url(url)
        if data:
            out.append(data)

    return out