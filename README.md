# Hacker News Podcast Generator

This application creates a Hacker News Podcast by taking the best links of any day on Hacker News, summarizing the article text
within the links using an API, and then synthesizing the text to speech using Google's new WaveNet-based Text-To-Speech API.

It will then upload the podcasts to a Google Cloud Storage bucket and create a podcast RSS feed for you, so you can submit it to iTunes or Google Play.

With little modifications, you can use this script to summarize any news website or aggregator, reddit, etc.

### Instructions

1. Copy config.py.example to config.py, and fill in the details.
AYLIEN_API_ID and AYLIEN_API_KEY are provided when creating a new Aylien account.
The Google API key and service account json file can be created from the cloud console.
You will also need to create a Google Storage bucket to store the podcasts and RSS file into.

2. Enable Cloud Text-To-Speech using the Google Cloud console.

3. Install a new virtualenv and run

    `pip install -r requirements.txt`

3. Run hn.py with the specific date (in ISO format) you'd like to create the podcast for. For example:

    `python hn.py --date=2019-07-26`

If you do not specify a date, it will use yesterday's date to generate the podcast.

### Useful links

* Audio Library: https://www.youtube.com/audiolibrary/music?ar=3

### TODO:

* Use the google API client library instead of sending an HTTP request
* Use it on Reddit :)
