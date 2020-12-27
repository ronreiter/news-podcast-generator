from config import *
import http.client
import json

headers = {
    'x-rapidapi-key': AYLIEN_RAPIDAPI_KEY,
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