# -*- coding: utf-8 -*-
import os
import json
import boto3
import pytz
import logging
from datetime import datetime
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter


BUCKET_NAME = os.environ['BUCKET_NAME']
s3 = boto3.resource('s3')
s3_bucket = s3.Bucket(BUCKET_NAME)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

now = datetime.now(pytz.timezone('Asia/Tokyo'))
now_date = now.strftime('%Y-%m-%d')

STOP_WORDS = {
    'こと', 'よう', 'そう', 'これ', 'それ', 'みたい', '良い', 'もん',
    'ため', 'やつ', 'さん', 'RT', 'ない', 'ほど', 'なん', '悪い', '自分',
    'の', 'そこ', 'どっち', '方', '僕', 'あと', '今日', '昨日', 'わけ', 'うち',
    '明日', '試合', 'プロ野球ニュース', 'ここ', 'プロ野球', '野球', 'はず',
    'seibulions', 'Seibulions', 'sbhawks',
    'RakutenEagles', 'Rakuteneagles', 'rakuteneagles', 'Rakuten_Eagles',
    'hanshin', 'BayStars', 'Bs2021', 'bs2021',
    'chibalotte', 'lovefighters', 'giants', 'tigers', 'carp',
    'swallows', 'Swallows', 'dragons', 'baystars',
    'プロ野球ニュース', 'NPB', 'もの', '東海ラジオ', 'radiko',
    'リーグ公式戦', 'Crap_Jikkyo', 'プロ野球選手', 'ところ', 'ダメ', '相手',
    'セリーグ', 'パリーグ', '投手', '野手', '今年', '去年', 'ドラステ', 'ドラゴンズステーション',
    '中日', '中日ドラゴンズ', 'スワローズ', 'ヤクルト', 'カープ', '広島東洋カープ', '広島カープ',
    '阪神タイガース', 'タイガース', 'kanpuri_hiro', 'nikkan_mashiba',
    '阪神', 'Tigers', '巨人', 'ジャイアンツ', 'オリックス', 'バファローズ', 'ソフトバンク', 'ホークス',
    '西武', 'ライオンズ', '楽天', 'イーグルス', '楽天イーグルス', 'ロッテ', 'マリーンズ', '日本ハム', 'ファイターズ',
    '最後', '早い', '無い', 'とき', 'まま', 'ええ', 'ツイート', 'リツイート', 'フォロー', '引用リツイート',
}


def str_replace(t):
    words = ['@', '#', ':', '\"', ' ', '　', '!', '！', '?', '？']
    for w in words:
        t = t.replace(w, '')
    return t


# 名詞・形容詞のみ抽出
def extraction(texts):
    a = Analyzer(token_filters=[CompoundNounFilter()])
    words = []
    for text in texts:
        tokens = a.analyze(text)
        for t in tokens:
            pos = t.part_of_speech.split(',')[0]
            if pos in {'名詞', '形容詞'}:
                t = t.base_form   # 基本形
                # t = t.surface   # 表層形
                t = str_replace(t)
                if t not in STOP_WORDS and t[:4] != 'http':
                    words.append(t)
    return ' '.join(words)


def extraction_s3_object():
    contents = []
    s3_objects = s3_bucket.meta.client.list_objects_v2(
        Bucket=BUCKET_NAME, Prefix=now_date)
    s3_objects = s3_objects['Contents']
    for o in s3_objects:
        object_name = o['Key']
        logger.info(f'{object_name} start.')
        obj = s3_bucket.Object(object_name)
        txt = obj.get()['Body'].read().decode('utf-8')
        txt = txt.split('\n')
        contents.append(extraction(txt))
    return ' '.join(contents)


def lambda_handler(event, context):
    contents = extraction_s3_object()
    s3_save_object = s3.Object(BUCKET_NAME, f'{now_date}/today.txt')
    s3_save_object.put(Body=contents)
    return {
        'statusCode': 200,
        'body': json.dumps('Done.')
    }
