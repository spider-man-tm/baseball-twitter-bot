import os
import json
import emoji
import pytz
import boto3
import logging
from requests_oauthlib import OAuth1Session
from datetime import datetime


AT = os.environ['ACCESS_TOKEN']
ATS = os.environ['ACCESS_TOKEN_SECRET']
CK = os.environ['CONSUMER_KEY']
CS = os.environ['CONSUMER_SECRET']
URL = os.environ['URL']
BUCKET_NAME = os.environ['BUCKET_NAME']

SEARCH = [
    '#seibulions', '#Bs2021', '#sbhawks',
    '#chibalotte', '#lovefighters', '#RakutenEagles',
    '#阪神タイガース', '#ジャイアンツ', '#広島東洋カープ',
    '#スワローズ', '#中日ドラゴンズ', '#baystars',
    '#NPB',
]
s3 = boto3.resource('s3')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def remove_emoji(src_str):
    return ''.join(c for c in src_str if c not in emoji.UNICODE_EMOJI)


def collect_tweets(word):
    twitter = OAuth1Session(CK, CS, AT, ATS)
    params = {
        'q': word,
        'count': 100,
        'result_type': 'recent',
        # 'exclude': 'retweets',
        'lang': 'ja'
    }
    res = twitter.get(URL, params=params)

    if res.status_code == 200:
        timeline = json.loads(res.text)
        # ツイートが1つも無かった場合
        if not len(timeline['statuses']):
            logger.info('Tweet not found.')
            return

        file_contents = ''
        for data in timeline['statuses']:
            file_contents += remove_emoji(data['text'] + '\n')

        now = datetime.now(pytz.timezone('Asia/Tokyo'))
        now_date = now.strftime('%Y-%m-%d')
        now_time = now.strftime('%H:%M:%S')
        KEY_NAME = f'{now_date}/{now_time}-{word}.txt'
        s3_object = s3.Object(BUCKET_NAME, KEY_NAME)
        s3_object.put(Body=file_contents)
        logger.info(f'finish searching to {word}.')
        return
    else:
        logger.error('Error of twitter API.')
        return


def lambda_handler(event, context):
    for word in SEARCH:
        collect_tweets(word)

    return {
        'statusCode': 200,
        'body': json.dumps('Done.')
    }
