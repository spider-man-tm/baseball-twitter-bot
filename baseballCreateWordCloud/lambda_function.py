import os
import json
import boto3
import pytz
import logging
import numpy as np
from io import BytesIO
from PIL import Image
from datetime import datetime
from requests_oauthlib import OAuth1Session
from wordcloud import WordCloud, ImageColorGenerator


AT = os.environ['ACCESS_TOKEN']
ATS = os.environ['ACCESS_TOKEN_SECRET']
CK = os.environ['CONSUMER_KEY']
CS = os.environ['CONSUMER_SECRET']
URL_TEXT = os.environ['URL_TEXT']
URL_MEDIA = os.environ['URL_MEDIA']
TWEET_BUCKET_NAME = os.environ['TWEET_BUCKET_NAME']
MASK_BUCKET_NAME = os.environ['MASK_BUCKET_NAME']
twitter = OAuth1Session(CK, CS, AT, ATS)

now = datetime.now(pytz.timezone('Asia/Tokyo'))
now_date = now.strftime('%Y-%m-%d')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def get_img_from_s3():
    """
    マスク画像の取得
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(MASK_BUCKET_NAME)
    res = bucket.Object('ground.jpeg').get()
    body = res['Body'].read()
    img = Image.open(BytesIO(body))
    img = np.asarray(img)
    return img


def get_txt_from_s3():
    """
    取得してきたtweetデータの取得
    """
    s3 = boto3.client('s3')
    key = now_date + '/today.txt'
    response = s3.get_object(Bucket=TWEET_BUCKET_NAME, Key=key)
    txt = response['Body'].read().decode('utf-8')
    return txt


def get_font_from_s3():
    """
    日本語の文字化け対策のためfontデータを取得
    """
    s3 = boto3.resource('s3')
    s3_bucket = s3.Bucket(MASK_BUCKET_NAME)
    font_file_path = '/tmp/font.ttc'
    s3_bucket.download_file('font.ttc', font_file_path)
    return font_file_path


def create_word_cloud():
    """
    word cloudの生成
    """
    mask = get_img_from_s3()
    text = get_txt_from_s3()
    font = get_font_from_s3()
    image_color = ImageColorGenerator(mask)
    wc = WordCloud(
        mask=mask,
        color_func=image_color,
        prefer_horizontal=1.0,
        max_words=1000,
        max_font_size=38,
        min_font_size=4,
        font_step=1,
        font_path=font,
        background_color='#d3f7ff',
        min_word_length=2,
        repeat=True,
    ).generate(text)
    wc = wc.to_array()
    wc = Image.fromarray(wc)
    return wc


def img_to_s3(img):
    """
    S3バケットにワードクラウドを保存
    """
    s3 = boto3.client('s3')
    bucket = TWEET_BUCKET_NAME
    key = f'{now_date}/word_cloud.png'
    tmp = u'/tmp/' + os.path.basename(key)
    img.save(tmp, 'PNG')
    s3.upload_file(Filename=tmp, Bucket=bucket, Key=key)


def twitter_post(img):
    """
    Twitterへの投稿
    """
    # PIL.Image.Image -> バイナリーへ変換
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, 'PNG')
    img = img_byte_arr.getvalue()

    files = {'media': img}
    req_media = twitter.post(URL_MEDIA, files=files)

    if req_media.status_code != 200:
        return 'Image update error.'

    media_id = json.loads(req_media.text)['media_id']

    message = '''のプロ野球関連ツイートまとめです。\n
                #seibulions #Bs2021 #sbhawks #chibalotte
                #lovefighters #RakutenEagles #阪神タイガース
                #ジャイアンツ #広島東洋カープ #スワローズ
                #中日ドラゴンズ #baystars #NPB'''

    params = {
        'status': f'{now_date}{message}',
        'media_ids': media_id
    }
    req = twitter.post(URL_TEXT, params=params)

    if req.status_code != 200:
        return 'Image update error.'

    return 'Tweet done.'


def lambda_handler(event, context):
    img = create_word_cloud()
    img_to_s3(img)
    message = twitter_post(img)
    logger.info(message)
    return {
        'statusCode': 200,
        'body': json.dumps('Done.')
    }
