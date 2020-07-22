import requests
import datetime
import json
import sys
import csv
import base64
import dateutil
from time import sleep
from requests.auth import HTTPBasicAuth
from dateutil.parser import parse  # pip3 install python-dateutil
import os
from slack import WebClient
from slack.errors import SlackApiError
s = requests.Session()

# add creds here and run the script
email = os.environ['SUPPORT_CENTER_EMAIL']
zdkey = os.environ['SUPPORT_CENTER_ZDKEY']
days_ago = 1  # only select articles modified with the past x days

client = WebClient(token=os.environ['SLACK_API_TOKEN'])

# add auth to the header for all future requests
auth2 = base64.b64encode('{}/token:{}'.format(email, zdkey).encode("utf-8"))
# s.auth = (email, zdkey)
# s.headers.update({'Authorization': 'Basic {}'.format(auth2)})
headers = {"Authorization": "Basic {}".format(
    auth2.decode("utf-8")), 'contentType': 'application/json'}

# set some datetimes as a point of reference
past = datetime.datetime.now() - datetime.timedelta(days=days_ago)
today = datetime.datetime.now()

# setting up some api urls
zd_url = 'https://circleci.zendesk.com/api/v2/help_center'
ep_articles = '{}/en-us/articles.json'.format(zd_url)

# get all of the articles from zendesk
articles = requests.get(ep_articles).json()
pages = articles['page_count']
article_list = articles['articles']

# the response is paginated, so we'll get the articles for every page
for page in range(2, pages + 1):
    article_list += requests.get(ep_articles,
                                 params={'page': page}).json()['articles']
    sleep(1)

# filter the articles to only select the ones within our date range
articles_filtered_date = [x for x in article_list if parse(
    x['updated_at']).replace(tzinfo=None) > past]
# print(articles_filtered_date[0]['html_url'])
# print(articles_filtered_date[0]['title'])


# go through each article and extract the vote data
for article in articles_filtered_date:
    # pull out needed details so we can make Slack blocks cleanly
    article_url = article['html_url']
    article_title = article['title']
    article_link = f"<{article_url}|{article_title}>"

    # do a lot of dark magic so that the timestamps are reasonably human-readable:
    # grab the created_at timestamp, use fromisoformat to break it apart,
    # then use ctime to make it nice, like so: Wed Nov  1 15:57:43 2017
    # otherwise they look like 2017-11-01T15:57:43Z
    created_timestamp = datetime.datetime.fromisoformat(
        article['created_at'].rstrip('Z')).ctime()
    updated_timestamp = datetime.datetime.fromisoformat(
        article['updated_at'].rstrip('Z')).ctime()

#   troubleshooting friend: uncomment the below line to pop open IPython when this runs
#    import IPython;IPython.embed()

    try:
        response = client.chat_postMessage(
            channel='#random',
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Support Center Article Updated: *" + article_link
                    }
                },
                # {
                #     "type": "section",
                #     "text": {
                #         "type": "mrkdwn",
                #         "text": article_link
                #     }
                # },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Updated:*\n{updated_timestamp}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Originally Created:*\n{created_timestamp}"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
        )
        # assert response["message"]["text"] == article['title']
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        # str like 'invalid_auth', 'channel_not_found'
        assert e.response["error"]
        print(f"Got an error: {e.response['error']}")
