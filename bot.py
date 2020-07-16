import requests
import datetime
import json
import sys
import csv
import base64
import dateutil
from time import sleep
from requests.auth import HTTPBasicAuth
from dateutil.parser import parse #pip3 install python-dateutil
import os
from slack import WebClient
from slack.errors import SlackApiError
s = requests.Session()

# add creds here and run the script
email = os.environ['SUPPORT_CENTER_EMAIL']
zdkey = os.environ['SUPPORT_CENTER_ZDKEY']
days_ago = 1 # only select articles modified with the past x days

client = WebClient(token=os.environ['SLACK_API_TOKEN'])

# add auth to the header for all future requests
auth2 = base64.b64encode('{}/token:{}'.format(email,zdkey).encode("utf-8"))
# s.auth = (email, zdkey)
# s.headers.update({'Authorization': 'Basic {}'.format(auth2)})
headers = {"Authorization": "Basic {}".format(auth2.decode("utf-8")), 'contentType': 'application/json'}

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
  article_list += requests.get(ep_articles, params={'page': page}).json()['articles']
  sleep(1)

# filter the articles to only select the ones within our date range
articles_filtered_date = [x for x in article_list if parse(x['updated_at']).replace(tzinfo=None) > past]
print(articles_filtered_date[0]['html_url'])
print(articles_filtered_date[0]['title'])


# go through each article and extract the vote data
for article in articles_filtered_date:
  article_url  = article['html_url']
  article_title = article['title']
  article_link = f"<{article_url}|{article_title}>"
  print(article_link)
  try:
    response = client.chat_postMessage(
        channel='#random',
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Support Center Article Updated"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": article_link
                }
            },
            {
                "type": "divider"
            }
            # {
            #     "type": "section",
            #     "fields": [
            #         {
            #             "type": "mrkdwn",
            #             "text": "Created At"
            #         },
            #         {
            #             "type": "mrkdwn",
            #             "text": "Created By"
            #         },
            #         {
            #             "type": "mrkdwn",
            #             "text": article['created_at']
            #         },
            #         {
            #             "type": "mrkdwn",
            #             "text": article['author_id']
            #         }
            #     ]
            # }
        ]
    )
    # assert response["message"]["text"] == article['title']
  except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["ok"] is False
    assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
    print(f"Got an error: {e.response['error']}")
  