import sys
# sys.path.append 다른 환경에서도 시스템변수 추가
# libs에 있는 라이브러리들을 불러서 import할수 있게 하는거
sys.path.append('./libs')
import logging
import requests
import pymysql
import bot
import json
import boto3
import base64
from boto3.dynamodb.conditions import Key, Attr
from secrect_key import MYSQL_KEY, TOKEN_, API_KEY

s3 = boto3.resource('dynamodb', region_name='ap-northeast-2', endpoint_url='http://dynamodb.ap-northeast-2.amazonaws.com')

logger = logging.getLogger() # 로깅에게 이름을 줄수있는 인스턴스화 
logger.setLevel(logging.INFO)   #로깅을 쓸수있게 해주는 함수
# 참고로 pymysql는 포트번호는 숫자로 해 주어야 한다... MYSQL_KEY['port'] =3306....
 
try:
    conn = pymysql.connect(MYSQL_KEY['host'], user=MYSQL_KEY['user'], passwd=MYSQL_KEY['password'], db=MYSQL_KEY['db'], port=MYSQL_KEY['port'], use_unicode=True, charset='utf8')
    cursor = conn.cursor()
except:
    logging.error("could not connect to rds")
    sys.exit(1)
try:
    dynamo_db = boto3.resource('dynamodb', region_name='ap-northeast-2', endpoint_url='http://dynamodb.ap-northeast-2.amazonaws.com')
except:
    logging.error("dynamo_db connection error")
    sys.exit(1)

# 테이블명 입력
table = dynamo_db.Table('best_track')

# bot.py 초기 class의 인스턴스를  생성한다. (access_token파라미터에 들어 간다.)
bot = bot.Bot(TOKEN_['PAGE_TOKEN'])

def lambda_handler(event, context):

    if 'params' in event.keys():

        if event['params']['querystring']['hub.verify_token'] == TOKEN_['VERIFY_TOKEN'] :
            return int(event['params']['querystring']['hub.challenge'])
        else:
            logging.error('wrong validation token')
            raise SystemExit
    else:
        response = event['entry'][0]['messaging'][0]
        user_id = response['sender']['id']
        logger.info(response) 
        
        artist_name = response['message']['text']

        query_generic = f"SELECT image_url, url, id FROM artists WHERE name = '{artist_name}'"
        cursor.execute(query_generic)
        raw =  cursor.fetchall()

        if len(raw) == 0:
            result_ = search_artist(cursor, artist_name)
            bot.send_text(user_id, result_)
            sys.exit(0)

        image_url, url, id =  raw[0]
        payload_generic = {
                    "template_type":"generic",
                    "elements":[{
                        "title":f"Artist Info: {artist_name}",
                        "image_url": image_url,
                        "subtitle":"information",
                        "default_action": {
                            "type": "web_url",
                            "url": url,
                            "webview_height_ratio": "full"
                            }
                        }]
                    }

        bot.send_attachment(user_id, "template", payload_generic)





        query = "SELECT t2.genre FROM artists t1 JOIN artist_genres t2 ON t2.artist_id = t1.id WHERE t1.name = '{}'".format(artist_name)

        cursor.execute(query)
        genres = []
        for (genre, ) in cursor.fetchall():
            genres.append(genre)

        text = f"{artist_name}의 장르에 관한 정보입니다. "
        bot.send_text(user_id, text)
        bot.send_text(user_id, ', '.join(genres))



        query = '''SELECT p1.name as related_artist, p2.distance FROM artists p1 JOIN 
        (select t1.name, t2.y_artist, t2.distance from artists t1 join related_artists t2 on         
        t2.artist_id = t1.id where t2.artist_id = '{}' and t2.distance != 0) p2 on 
        p1.id = p2.y_artist order by p2.distance limit 5;'''.format(id)

        cursor.execute(query)

        for (related_artist, distance, ) in cursor.fetchall():
            distance_result = 100 - (distance * 100)
            text = f"{artist_name}와 가장 유사한 아티스트 정보입니다 {related_artist}와 {artist_name}, {distance_result}%의 유사도를 가지고 있네요!!"
            bot.send_text(user_id, text)


        query = '''SELECT p1.name as related_artist, p2.distance FROM artists p1 JOIN 
        (select t1.name, t2.y_artist, t2.distance from artists t1 join related_artists t2 on         
        t2.artist_id = t1.id where t2.artist_id = '{}' and t2.distance != 0) p2 on 
        p1.id = p2.y_artist order by p2.distance limit 5;'''.format(id)


        cursor.execute(query)
        first_recommend = [related_artist_first for (related_artist_first, _, ) in  cursor.fetchall() ]
        if first_recommend  == []:  
            text = f"현재 바로 추가된  아티스트의 경우 업데이트 중에 있습니다. 대신 아티스트의 정보로 이동하겠습니다. 불편을 들여서 죄송합니다"
            bot.send_text(user_id, text)     

        query_generic = f"SELECT image_url, url, id as id_ FROM artists WHERE name = '{first_recommend[0]}'"
        cursor.execute(query_generic)
        raw =  cursor.fetchall()

        if len(raw) == 0:
            result_ = search_artist(cursor, first_recommend[0])
            bot.send_text(user_id, result_)
            sys.exit(0)

        print(raw)
        image_url, url, id_ =  raw[0]
        payload_generic = {
                    "template_type":"generic",
                    "elements":[{
                        "title":f"Artist Info: {first_recommend[0]}",
                        "image_url": image_url,
                        "subtitle":"information",
                        "default_action": {
                            "type": "web_url",
                            "url": url,
                            "webview_height_ratio": "full"
                            }
                        }]
                    }

        query = "SELECT t2.genre FROM artists t1 JOIN artist_genres t2 ON t2.artist_id = t1.id WHERE t1.name = '{}'".format(first_recommend[0])

        cursor.execute(query)
        genres = []
        for (genre, ) in cursor.fetchall():
            genres.append(genre)

        text = f"가장 유사도가 높은 {first_recommend[0]} 추천드립니다!!!"
        bot.send_text(user_id, text)       

        text = f"{first_recommend[0]}의 장르에 관한 정보입니다. "
        bot.send_text(user_id, text)
        bot.send_text(user_id, ', '.join(genres))

        bot.send_attachment(user_id, "template", payload_generic)
        
        response_ = table.query(
            KeyConditionExpression = Key('artist_id').eq(id_),
            FilterExpression = Attr('popularity').gt(75)
        )
        text = f'''{first_recommend[0]}의 인기도가 가장 높은 노래들도 추천해 드립니다''' 
        bot.send_text(user_id, text)       
        text = f'''{response_['Items'][0]['name']}의 해외 평점은 100점 만점에 {response_['Items'][0]['popularity']} 정도 에요'''
        bot.send_text(user_id, text)

        payload_generic = {
                    "template_type":"generic",
                    "elements":[{
                        "title":f"Track info: {response_['Items'][0]['name']}",
                        "image_url": response_['Items'][0]['album']['images'][0]['url'],
                        "subtitle":"information",
                        "default_action": {
                            "type": "web_url",
                            "url": response_['Items'][0]['external_urls']['spotify'],
                            "webview_height_ratio": "full"
                            }
                        }]
                    }

        bot.send_attachment(user_id, "template", payload_generic)
        sys.exit(0)


def get_headers_(c_id, c_pw):

    endpoint            = "https://accounts.spotify.com/api/token"
    en_decoded_         = base64.b64encode(f"{c_id}:{c_pw}".encode('utf-8')).decode('ascii')
    header_             = { "Authorization" :  f"Basic {en_decoded_}"}
    payload             = { "grant_type" : "client_credentials"}

    sign_in = requests.post(endpoint, data=payload, headers=header_)
    
    access_token        = json.loads(sign_in.text)['access_token'] 
    headers             = {"Authorization":f"Bearer {access_token}"}
    
    return headers

def insert_row(cursor, data, table):

    placeholders = ', '.join(['%s'] * len(data))
    columns = ', '.join(data.keys())
    key_placeholders = ', '.join([f'{k}=%s' for k in data.keys()])
    sql = f"INSERT INTO {table} ( {columns} ) VALUES ( {placeholders} ) ON DUPLICATE KEY UPDATE {key_placeholders}"
    cursor.execute(sql, list(data.values())*2)





# 람다안에서 람다함수를 호출하는 함수를 만든다. 
def invoke_lambda(function_name, payload, invocation_type='Event'):

    lambda_client = boto3.client('lambda')

    invoke_response = lambda_client.invoke(
        functionName   = function_name,
        invocationType = invocation_type,
        Payload        = json.dumps(payload)
    )

    if invoke_response['StatusCode'] not in [200,202, 204]:
        logging.error(f"ERROR :invoking lamda :{function_name} fail")
    
    return invoke_response







# 사용자의 요청된 아티스트가 없을 때 검색하는 함수
def search_artist(cursor ,artist_name):

    headers = get_headers_(API_KEY['c_id'], API_KEY['c_pw'])

    params = {
        "q"     : f"{artist_name}",
        "type"  : "artist",
        "limit" : "1"
    }
    results = requests.get("https://api.spotify.com/v1/search", params=params, headers=headers) 
    results_loaded = json.loads(results.text)

    if results_loaded['artists']['items'] == []:
        return "아티스트를 찾을 수가 없네요... 가수명을 영문으로 대소문자, 띄어쓰기를 지켜서 다시 한번 해 보세요"
    artist = {}

    artist_raw = results_loaded['artists']['items'][0]
    if artist_raw['name'] == params['q']:

        artist.update(
            {
                'id': artist_raw['id'],
                'name': artist_raw['name'],
                'followers': artist_raw['followers']['total'],
                'popularity': artist_raw['popularity'],
                'url': artist_raw['external_urls']['spotify'],
                'image_url': artist_raw['images'][0]['url']
            }
        )
        for i in artist_raw['genres']:
            
            if len(artist_raw['genres']) != 0:
                insert_row(cursor, {'artist_id': artist_raw['id'], 'genre':i}, 'artist_genres')

        insert_row(cursor, artist, 'artists')
        conn.commit()
        # invoke_lambda('best_tracks', payload={'artist_id': artist_raw['id']})
        # invoke_lambda('artist_distance', payload={'artist_id': artist_raw['id'], 'user_id': user_id})

        return "분석을 완료하였습니다!!! 다시 검색 해 주세요"

    return "아티스트를 찾을 수가 없네요... 가수명을 영문으로 대소문자, 띄어쓰기를 지켜서 다시 한번 해 보세요"

