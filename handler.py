import json
import boto3
from boto3.dynamodb.conditions import Key
import psycopg2
from collections import defaultdict
from datetime import datetime, timedelta
from intervaltree import Interval, IntervalTree
from requests_futures.sessions import FuturesSession
import requests
import os 

#faire une dizaine de requete api
api_key = 'c03628ad-7301-4577-b6bb-153cc75951a9'
TIME_END = '18:00'
BSB_CLOSURE = '18'
reservation_link = 'https://reservation.affluences.com/api/resources/'
resource_name = {'BSB': 'ba970374-77b3-4619-af1f-020ee44dcfc0', 'BSG': '7986d46a-a236-4280-a0a0-21e6cc724094'}
sample_resource = {'BSB': '8445', 'BSG': '29638'}

def send_all_good_dict(auth_token = "True"):
    if auth_token != "True":
        body = f'auth_token{auth_token}'
    else:
        body = "True"
    return {
                'statusCode': 200,
                'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Credentials': True,
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                'body': json.dumps(body)
            }

send_check_mail_dict = {
            'statusCode': 200,
            'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                },
            'body': json.dumps('False')
        }


send_error_dict = {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Credentials': True,
                    },
                    'body': json.dumps('ERROR')
                }

send_email_not_found_dict = {
                            'statusCode': 200,
                            'headers': {
                                    'Content-Type': 'application/json',
                                    'Access-Control-Allow-Origin': '*',
                                    'Access-Control-Allow-Credentials': True,
                                },
                            'body': json.dumps('email_not_found')
                }

send_already_res_dict = {
                            'statusCode': 200,
                            'headers': {
                                    'Content-Type': 'application/json',
                                    'Access-Control-Allow-Origin': '*',
                                    'Access-Control-Allow-Credentials': True,
                                },
                            'body': json.dumps('already_res')
                }


def create_user(dynamo_table, email):
    user = dynamo_table.put_item(
        Item={
                'user_email': email
            }
        )
    return user

def send_token(email, table):
    #fetch and change api_key in dynamo TO DO 
    print('implement if api_key does not work ask for one')
    url = 'https://reservation.affluences.com/api/myreservations/token'
    headers = {'Content-type': 'application/json', 'host': 'reservation.affluences.com', 'user-identifier': api_key}
    myobj = {"email": email }
    r = requests.post(url, data=json.dumps(myobj), headers=headers) 
    r_json = json.loads(r.content)
    print(r_json)
    print(url)
    print(headers)
    print(myobj)
    if 'error' in r_json and (r_json['error'] == "email_format" or r_json['error'] == "not_found"):
        print('email_not_found')
        return send_email_not_found_dict
    if 'error' in r_json and r_json['error'] == "apikey_no_device":
        print('wrong_api_key')
        return send_all_good_dict('000000')
    if ('error' in r_json) or ('request_uuid' not in json.loads(r.content)):
        print('unknown_error')
        return send_error_dict
    request_uuid = json.loads(r.content)['request_uuid']
    table.update_item(
        Key={
            'user_email': email
        },
        UpdateExpression='SET request_uuid = :val1',
        ExpressionAttributeValues={
            ':val1': request_uuid
        }
    )
    return send_check_mail_dict

def get_auth_token(email, request_uuid, table):
    url = f'https://reservation.affluences.com/api/myreservations/token?request_uuid={request_uuid}'
    headers = {'Content-type': 'application/json'}
    r = requests.get(url,  headers=headers)
    print(r)
    print(url)
    print(headers)
    r_json = json.loads(r.content)
    if 'auth_token' not in r_json:
        return None
    auth_token = r_json['auth_token']
    table.update_item(
        Key={
            'user_email': email
        },
        UpdateExpression='SET auth_token = :val1',
        ExpressionAttributeValues={
            ':val1': auth_token
        }
    )
    return auth_token
    
def get_my_resa(auth_token):
    url = 'https://reservation.affluences.com/api/myreservations'
    headers = {'Content-type': 'application/json', 'authorization': f'Bearer {auth_token}', 'host': 'reservation.affluences.com'}
    r = requests.get(url,  headers=headers)
    print(r)
    print(url)
    print(headers)
    return r

def nullify_old_auth_token(email, table):
    table.update_item(
        Key={
            'user_email': email
        },
        UpdateExpression='SET auth_token = :val1',
        ExpressionAttributeValues={
            ':val1': 'old'
        }
    )

def check_if_good_library(email, bibli, auth_token):
    print('check if good library')
    session = FuturesSession()
    now = datetime.now() 
    current_date = f'{now.year}-{now.month}-{now.day}'
    futures = []
    reserve(futures, session, sample_resource[bibli], '10:00', '23:59', email, current_date, 0)
    result = futures[0][0].result()
    print(result.content)
    if 'error' in json.loads(result.content) and json.loads(result.content)['error'] == 'email_requirements_do_not_match':
        return send_email_not_found_dict
    else: 
        return send_all_good_dict(auth_token)

def check_if_auth_token_valid_and_good_library(auth_token, email, table, bibli):
    print('check if auth_token is good')
    r = get_my_resa(auth_token)
    r_json = json.loads(r.content)
    if 'results' not in r_json:
        nullify_old_auth_token(email, table)
        return send_token(email, table)
    if bibli != 'none':
        return check_if_good_library(email, bibli, auth_token)
    else:
        return send_all_good_dict(auth_token)
     

def user_email_sent(event, context):
    # voir feuille
    #est ce que email existe dans dynabo ? 
    #oui => est ce qu'il y a un request_uuid?
        #oui => est ce qu'il y a un auth_token ? 
            #oui => est ce qu'il est valide?
                #oui => ON DIT OK ET ON DISPLAY NEW FIELDS
                #non => demande de request_uuid nouveau
            #non on renvoie un mail avec un nouveau request_uuid
        #non => demande de request_uuid
    #non => enregistrer et demande de request_uuid
    try:
        print(event)
        email = event['pathParameters']['email']
        bibli = event['pathParameters']['bibli']
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('bsb_users')
        result = table.query(
            KeyConditionExpression=Key('user_email').eq(email)
        )

        if not result['Items']:
            user = create_user(table, email)
            return send_token(email, table)


        user = result['Items'][0]
        if 'request_uuid' not in user:
            return send_token(email, table)
            

        if (('auth_token' not in user) or (user['auth_token'] == 'old')):
            auth_token = get_auth_token(email, user['request_uuid'], table)
            if auth_token is None:
                return send_token(email, table)
        else:
            auth_token = user['auth_token']
        
        return check_if_auth_token_valid_and_good_library(auth_token, email, table, bibli)
    except Exception as e:
        print(e)
        return send_error_dict

def connect_to_rds():
    rds_host  = 'afflubot.chmploavcitj.eu-west-3.rds.amazonaws.com'
    rds_username = 'afflubot'
    rds_user_pwd = 'afflubot828378YH029'
    rds_db_name = 'postgres'
    conn_string = "host=%s user=%s password=%s dbname=%s" % \
                    (rds_host, rds_username, rds_user_pwd, rds_db_name)
    conn = psycopg2.connect(conn_string)
    return conn


def verify_if_already_res(cursor, email, heure_debut_request, heure_fin_request):
    cursor.execute(f"Select * from demandes_reservations where date = '{email}'::date and valide = 0") 
    raw = cursor.fetchall()
    for line in raw:
        heure_debut = line[4]
        heure_fin = line[5]
        if (heure_debut_request > heure_fin_request) or (heure_debut < '10:00') or (heure_fin > '20:00') or ((heure_fin_request > heure_debut) and (heure_debut_request < heure_fin)):
            print('pb request')
            return 'already_res'
    return 'all_good'

def create_reservation_request(event, context):
    try:
        print(event) 
        body = json.loads(event['body'])
        v0 = body["email"]
        v1 = body["auth_token"]
        v2 = body["date"]
        v3 = body["heure_debut"]
        v4 = body["heure_fin"]
        v5 = body["valide"]
        v6 = body["type"]
        v7 = body["etablissement"]
        if "etage_pref" in body:
            v8 = body['etage_pref']
        else:
            v8 = -1
        if "etage_pref_mandatory" in body:
            v9 = body['etage_pref_mandatory']
        else:
            v9 = False
        if "morcelle" in body:
            v10 = body['morcelle']
        else:
            v10 = False
        if "morcelle_h_already_taken" in body:
            v11 = body['morcelle_h_already_taken']
        else:
            v11 = -1
        #TO DO
        #validation rule tout est présent
        # valdiation rule for email (later first lambda checks if dynamo db ok then here step function) TO DO
        #validation rule date >= ajr (prio 4) & strftime("%Y-%m-%d"), 
        # validation rule 10h <= heure_debut < heure_fin <= 20h
        # validation rule : pas d'envelop deja present dans la bdd (prio 1)
        # envoi de mail contact @ afflubot : demande de reservaiton de temps a temps (prio 3)
        #annulation de demande de reservation  (prio 2)
        conn = connect_to_rds()
        cursor = conn.cursor()
        res = verify_if_already_res(cursor, v2, v3, v4)
        if res != 'all_good':
            return send_already_res_dict
        cursor.execute("INSERT INTO demandes_reservations (email,auth_token, date, heure_debut, heure_fin, valide, type, etablissement, etage_pref, etage_pref_mandatory, morcelle, morcelle_h_already_taken) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11))
        conn.commit()
        cursor.close()
        conn.close()
        return send_all_good_dict()
    except Exception as e:
        print(e)
        return send_error_dict

def send_reservation_request(event, context):
    try:
        print(event) 
        email = event['pathParameters']['email']
        conn = connect_to_rds()
        cursor = conn.cursor()
        cursor.execute(f"Select * from demandes_reservations where email = '{email}' and date >= current_date and valide = 0;") 
        raw = cursor.fetchall()
        raw.sort(key=lambda tup: tup[3])
        return {
            'statusCode': 200,
            'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                },
            'body': json.dumps(raw, default=str)
        }
    except Exception as e:
        print(e)
        return send_error_dict


def reservation_request_annulation(event, context):
    print(event)
    try:
        body = json.loads(event['body'])
        id_request = body["id_request"]
        conn = connect_to_rds()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE demandes_reservations SET valide = -1 where id = {id_request}")
        conn.commit()
        cursor.close()
        conn.close()
        return send_all_good_dict()
    except Exception as e:
        print(e)
        return send_error_dict

def delay_real_reservation(event, context):
    try:
        print(event) 
        body = json.loads(event['body'])
        cancel_token = body["cancel_token"]
        resource_id = body["resource_id"]
        date = body["date"]
        stop_hour = body["stop_hour"]
        email = body["email"]
        start_hour = body["start_hour"]

        response = requests.delete(
        f'https://reservation.affluences.com/api/cancelReservation/?email_token={cancel_token}'
        )
        print(response)
        if response.status_code == 200:
            #while response code not ok... change end_time with duration
            url = f'https://reservation.affluences.com/api/reserve/{resource_id}'
            myobj = {"date": date,
                    "email": email,
                    "end_time": stop_hour,
                    "note": None,
                    "person_count": None,
                    "start_time": start_hour,
                    "user_firstname": None,
                    "user_lastname": None,
                    "user_phone": None}
            headers = {f'Content-type': 'application/json', 'user-identifier': api_key}
            x = requests.post(url, data=json.dumps(myobj), headers=headers)
            print(x)
            print(x.status_code)
            if x.status_code != 201:
                return send_error_dict
            return send_all_good_dict()
        else:
            print('delete error')
            return send_error_dict
    except Exception as e:
        print(e)
        return send_error_dict

def fetchResRequests(event, context):
    # order by duration resa and by etage to do
    # to do : if ajr : time > time actuel, if 2morow time > 10:00::time 
    # to do lower case email when connexion
    try:
        print(event)
        conn = connect_to_rds()
        cursor = conn.cursor()
        #change interval dynamic
        cursor.execute(f"Select * from demandes_reservations where date = current_date + INTERVAL '{os.environ['day']} DAY' and valide = 0 and etablissement = '{os.environ['etablissement']}' and heure_debut::time >= '10:00'::time and type='{os.environ['resource_id']}' order by (heure_fin::time - heure_debut::time) desc") 
        res_requests = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        print(res_requests)
        return json.dumps(res_requests, default=str)
    except Exception as e:
        print(e)




def request_for_library_availibilities_for_date_and_hour(resa_link, res_name, date, type_res):
    r = requests.get(f'{resa_link}{res_name}/available?date={date}&type={type_res}')
    print(f'{resa_link}{res_name}/available?date={date}&type={type_res}')
    print(r.content)
    return json.loads(r.content)

def organize_res_in_dict(event):
    res_requests = IntervalTree()
    for res in event:
        hour_start = res[4]
        hour_end = res[5]
        hour_start_mod = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5')
        hour_end_mod = float(f'{hour_end[:2]}') if hour_end[3:] == '00' else float(f'{hour_end[:2]}.5')
        res_requests[hour_start_mod:hour_end_mod] = f'{hour_end_mod - hour_start_mod}////////{res[1]}////////{res[0]}'
    return res_requests

def reserve(futures, session, resource_id, hour_start, hour_end, email, date, request_id_postgre):
    try:
        hour_start = str(hour_start)
        hour_start = f'{hour_start[:2]}:00' if hour_start[3:] == '0' else f'{hour_start[:2]}:30'
        hour_end = str(hour_end)
        hour_end = f'{hour_end[:2]}:00' if hour_end[3:] == '0' else f'{hour_end[:2]}:30'
        print(f'reserve on {resource_id}')
        url = f'https://reservation.affluences.com/api/reserve/{resource_id}'
        myobj = {"date": date,
                "email": email,
                "end_time": hour_end,
                "note": None,
                "person_count": None,
                "start_time": hour_start,
                "user_firstname": None,
                "user_lastname": None,
                "user_phone": None}
        headers = {f'Content-type': 'application/json', 'user-identifier': api_key}
        futures.append([session.post(url, data=json.dumps(myobj), headers=headers), request_id_postgre])
        return futures
    except Exception as e:
        print(e)


def take_data_for_sorted_list(elem):
    return elem.data


def reserveRequests(event, context):
    try:
        print(event)
        event = json.loads(event)
        if len(event) == 0:
            return
        futures = []
        session = FuturesSession()
        #to change
        now = datetime.now() + timedelta(days=int(os.environ['day']))
        current_date = f'{now.year}-{now.month}-{now.day}'
        print(f'searching for {current_date}')
        content = request_for_library_availibilities_for_date_and_hour(reservation_link, resource_name[os.environ['etablissement']], current_date, os.environ['resource_id'])
        res_requests = organize_res_in_dict(event)
        print(res_requests)
        for res in content:
            if len(res['hours']) == 0:
                break
            lock = False
            for i, h in enumerate(res['hours']):
                if i == 0:
                    hour_start = h['hour']
                    hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 
                if (h['places_available'] == 0) and (lock == False):
                    hour_end = h['hour']
                    hour_end = float(f'{hour_end[:2]}') if hour_end[3:] == '00' else float(f'{hour_end[:2]}.5') 
                    set_results = sorted(res_requests.envelop(hour_start, hour_end), key=take_data_for_sorted_list, reverse=True)
                    if len(set_results) > 0:
                        print(set_results)
                        req_to_res = set_results.pop()  
                        #to avoid email with same separator char
                        data = req_to_res.data.split('////////')
                        futures = reserve(futures, session, res['resource_id'], req_to_res.begin, req_to_res.end, data[1], current_date, data[2])
                        res_requests.remove(Interval(req_to_res.begin, req_to_res.end, req_to_res.data))
                    lock = True
                if (h['places_available'] == 1) and (lock == True):
                    hour_start = h['hour']
                    hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 
                    lock = False
                if (i == (len(res['hours']) - 1)) and (lock == False):
                    hour_end = float(f'{BSB_CLOSURE}')
                    set_results = set_results = sorted(res_requests.envelop(hour_start, hour_end), key=take_data_for_sorted_list, reverse=True)
                    if len(set_results) > 0:
                        print(set_results)
                        req_to_res = set_results.pop()
                        data = req_to_res.data.split('////////')
                        futures = reserve(futures, session, res['resource_id'], req_to_res.begin, req_to_res.end, data[1], current_date, data[2])
                        res_requests.remove(Interval(req_to_res.begin, req_to_res.end, req_to_res.data))
                    lock = False
        requests_validated = []
        for future in futures:
            result = future[0].result()
            print(result.content)
            if result.status_code <= 201:
                requests_validated.append(future[1])
        print(requests_validated)
        futures.clear()
        return requests_validated
        #don't forget to change in database valide to 1 and stop function stop if no res, implement for today and tomorow, and for every resource type, change data type, test, wording, deploy
    except Exception as e:
        print(e)

def validateRequests(event, context):
    try:
        print(event)
        if len(event) == 0:
            return
        
        conn = connect_to_rds()
        cursor = conn.cursor()
        for res_id in event:
            cursor.execute(f"UPDATE demandes_reservations SET valide = 1 where id = {int(res_id)}")
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)

