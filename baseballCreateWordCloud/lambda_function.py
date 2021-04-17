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


STOP_WORDS = {
    'こと', 'よう', 'そう', 'これ', 'それ', 'みたい', '良い', 'もん', 'いい',
    'ため', 'やつ', 'さん', 'RT', 'ない', 'ほど', 'なん', '悪い', '自分',
    'の', 'そこ', 'どっち', '方', '僕', 'あと', '今日', '昨日', 'わけ', 'うち',
    '明日', '試合', 'プロ野球ニュース', 'ここ', 'プロ野球', '野球', 'はず',
    'seibulions', 'Seibulions', 'sbhawks', 'みんな', 'みなさま',
    'RakutenEagles', 'Rakuteneagles', 'rakuteneagles', 'Rakuten_Eagles',
    'hanshin', 'BayStars', 'Bs2021', 'bs2021', 'bs_ponta',
    'chibalotte', 'lovefighters', 'giants', 'tigers', 'carp',
    'swallows', 'Swallows', 'dragons', 'baystars', 'バファローズポンタ',
    'プロ野球ニュース', 'NPB', 'もの', '東海ラジオ', 'radiko', 'DAZN',
    'リーグ公式戦', 'Crap_Jikkyo', 'プロ野球選手', 'ところ', 'ダメ', '相手',
    'セリーグ', 'パリーグ', '投手', '野手', '今年', '去年', 'ドラステ', 'ドラゴンズステーション',
    '中日', '中日ドラゴンズ', 'スワローズ', 'ヤクルト', 'カープ', '広島東洋カープ', '広島カープ',
    '阪神タイガース', 'タイガース', 'DeNA', 'ベイスターズ', 'kanpuri_hiro', 'nikkan_mashiba',
    '阪神', 'Tigers', '巨人', 'ジャイアンツ', 'オリックス', 'バファローズ',
    'ソフトバンク', 'ホークス', '埼玉西武ライオンズ', 'こちら', 'LCOLLECTION',
    '西武', 'ライオンズ', '楽天', 'イーグルス', '楽天イーグルス', 'ロッテ', 'マリーンズ', '日本ハム', 'ファイターズ',
    '最後', '早い', '無い', 'とき', 'まま', 'ええ', 'ツイート', 'リツイート', 'フォロー', '引用リツイート',
    'リーグ順位表', '本日', 'https co', '選手', '欲しい', 'PL', 'CL', 'リーグ試合結果',
    '公式戦', '予告先発', 'amp', 'kyojin', '結果', 'ほしい', 'よい', 'スタメン',
}


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
        max_font_size=36,
        min_font_size=4,
        font_step=1,
        font_path=font,
        stopwords=STOP_WORDS,
        background_color='#d3f7ff',
        min_word_length=1,
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
#seibulions #Bs2021 #sbhawks #chibalotte #lovefighters #RakutenEagles #阪神タイガース #ジャイアンツ #広島東洋カープ #スワローズ #中日ドラゴンズ #baystars'''

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
