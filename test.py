import boto3
from boto3.dynamodb.conditions import Key
import json
import psycopg2 
from datetime import datetime, timedelta
from collections import defaultdict

def fetch(conn, query):
    result = []
    print("Now executing: {}".format(query))
    cursor = conn.cursor()
    cursor.execute(query)

    raw = cursor.fetchall()
    for line in raw:
        result.append(line)

    return result
    

def create_conn():
    conn = None
    try:
        #rds_host  = os.environ.get('RDS_HOST')
        #rds_username = os.environ.get('RDS_USERNAME')
        #rds_user_pwd = os.environ.get('RDS_USER_PWD')
        #rds_db_name = os.environ.get('RDS_DB_NAME')
        rds_host  = 'afflubot.chmploavcitj.eu-west-3.rds.amazonaws.com'
        rds_username = 'afflubot'
        rds_user_pwd = 'afflubot828378YH029'
        rds_db_name = 'postgres'
        conn_string = "host=%s user=%s password=%s dbname=%s" % \
                        (rds_host, rds_username, rds_user_pwd, rds_db_name)
        print(conn_string)
        conn = psycopg2.connect(conn_string)
    except:
        print("Cannot connect.")
    return conn

def take_second(elem):
    return elem.data
import json
import boto3
from boto3.dynamodb.conditions import Key
import psycopg2
from collections import defaultdict
from datetime import datetime, timedelta
import requests
import os 

#faire une dizaine de requete api
api_key = 'c03628ad-7301-4577-b6bb-153cc75951a9'
TIME_END = '18:00'
BSB_CLOSURE = '18'
reservation_link = 'https://reservation.affluences.com/api/resources/'
resource_name = {'bsb': 'ba970374-77b3-4619-af1f-020ee44dcfc0'}
bsb_resource_id = {'inscription':'698', 'info': '701', 'normal' : '702'}

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

def check_if_auth_token_valid(auth_token, email, table):
    print('check if auth_token is good')
    r = get_my_resa(auth_token)
    r_json = json.loads(r.content)
    if 'results' not in r_json:
        nullify_old_auth_token(email, table)
        return send_token(email, table)
        
    if (len(r_json['results']) > 0) and (r_json['results'][0]['site_name'] != 'BSB - Bibliothèque Sainte-Barbe'):
        return send_email_not_found_dict
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
        
        return check_if_auth_token_valid(auth_token, email, table)
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
        cursor.execute(f"Select * from demandes_reservations where date = current_date + INTERVAL '{'0'} DAY' and valide = 0 and heure_debut::time >= '10:00'::time and type='702' order by (heure_fin::time - heure_debut::time) desc") 
        res_requests = cursor.fetchall()
        print(res_requests)
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
    return json.loads(r.content)

def organize_res_in_dict(event):
    res_requests = IntervalTree()
    for res in event:
        hour_start_mod = float(f'{res[4][:2]}') if res[4][3:] == '00' else float(f'{res[4][:2]}.5')
        hour_end_mod = float(f'{res[5][:2]}') if res[5][3:] == '00' else float(f'{res[5][:2]}.5')
        res_requests[hour_start_mod:hour_end_mod] = f'{hour_end_mod - hour_start_mod}////////{res[1]}////////{res[0]}'
    return res_requests

futures = []
def reserve(session, resource_id, hour_start, hour_end, email, date, request_id_postgre):
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
        session = FuturesSession()
        #to change
        now = datetime.now() + timedelta(days=int('0'))
        current_date = f'{now.year}-{now.month}-{now.day}'
        print(f'searching for {current_date}')
        content = b'[{"resource_id":8190,"resource_name":"Charti\xc3\xa8re  - 217","resource_type":702,"granularity":30,"time_slot_count":20,"static_time_slot":false,"reservations_by_timeslot":null,"note_available":false,"note_required":false,"note_description":null,"description":"2e \xc3\xa9tage","capacity":1,"site_timezone":"Europe/Paris","user_name_required":false,"user_phone_required":false,"user_name_available":false,"user_phone_available":false,"time_before_reservations_closed":null,"min_places_per_reservation":null,"max_places_per_reservation":null,"services":[],"image_url":null,"hours":[{"hour":"10:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"11:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"11:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"12:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"12:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"13:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"13:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"14:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"14:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"15:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"15:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"16:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"16:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"17:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"17:30","state":2,"reservations":[],"person_count":0,"places_available":0,"places_bookable":0}]},{"resource_id":8191,"resource_name":"Charti\xc3\xa8re  - 218","resource_type":702,"granularity":30,"time_slot_count":20,"static_time_slot":false,"reservations_by_timeslot":null,"note_available":false,"note_required":false,"note_description":null,"description":"2e \xc3\xa9tage","capacity":1,"site_timezone":"Europe/Paris","user_name_required":false,"user_phone_required":false,"user_name_available":false,"user_phone_available":false,"time_before_reservations_closed":null,"min_places_per_reservation":null,"max_places_per_reservation":null,"services":[],"image_url":null,"hours":[{"hour":"10:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"11:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"11:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"12:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"12:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"13:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"13:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"14:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"14:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"15:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"15:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"16:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"16:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"17:00","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1},{"hour":"17:30","state":1,"reservations":[],"person_count":0,"places_available":1,"places_bookable":1}]}]'
        print(event)
        content = json.loads(content)
        res_requests = organize_res_in_dict(event)
        print(res_requests)
        for res in content:
            print(res['hours'])
            if len(res['hours']) == 0:
                break
            lock = False
            print('ok')
            
            for i, h in enumerate(res['hours']):
                if i == 0:
                    print('ok2')
                    hour_start = h['hour']
                    hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 
                if (h['places_available'] == 0) and (lock == False):
                    print('ok3')
                    hour_end = h['hour']
                    hour_end = float(f'{hour_end[:2]}') if hour_end[3:] == '00' else float(f'{hour_end[:2]}.5') 
                    set_results = sorted(res_requests.envelop(hour_start, hour_end), key=take_data_for_sorted_list, reverse=True)
                    print(set_results)
                    if len(set_results) > 0:
                        print('IM HERE')
                        print(set_results)
                        req_to_res = set_results.pop()  
                        #to avoid email with same separator char
                        data = req_to_res.data.split('////////')
                        reserve(session, res['resource_id'], req_to_res.begin, req_to_res.end, data[1], current_date, data[2])
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
                        print('IM HERE2')
                        print(set_results)
                        req_to_res = set_results.pop()
                        data = req_to_res.data.split('////////')
                        reserve(session, res['resource_id'], req_to_res.begin, req_to_res.end, data[1], current_date, data[2])
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

def seek_saturday_opening(event, context):
    result = request_for_library_availibilities_for_date_and_hour(reservation_link, resource_name['bsb'], '2020-10-26', bsb_resource_id['normal'])
    if len(result) > 0:
        print(datetime.now() )

if __name__ == "__main__":
    '''
    a = fetchResRequests(None, None)
    print(a)
    reserveRequests(a, None)
    

    a = IntervalTree([Interval(10.0, 10.5, '0.5antoine.salamitou@outlook.fr'), Interval(10.5, 12.0, '1.5antoine.salamitou@outlook.fr'), Interval(12.0, 14.0, '2.0antoine.salamitou@outlook.fr'), Interval(14.0, 17.0, '3.0antoine.salamitou@outlook.fr'), Interval(17.5, 18.0, '0.5antoine.salamitou@outlook.fr')])
    
    print(sorted(a, key=take_second))
    urls = [
    'http://www.heroku.com',
    'http://tablib.org',
    'http://httpbin.org',
    'http://python-requests.org',
    'http://kennethreitz.com',
    'http://kennethreitz.com',
    ]

    rs = (grequests.get(u).response for u in urls)
    print(grequests.map(rs))
    futures = []
    for x in range(10):
        print(datetime.now())
        futures.append(pool.map_async(requests.get, ['http://google.com/']))
        print(datetime.now())
    # futures is now a list of 10 futures.
    for future in futures:
        print(future.get())

    available_hours = IntervalTree()
    event = [[13, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-22", "14:00", "17:00", 0.0, "702", "bsb", -1, False, False, -1], [12, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-22", "12:00", "14:00", 0.0, "702", "bsb", -1, False, False, -1], [15, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-22", "10:30", "12:00", 0.0, "702", "bsb", -1, False, False, -1], [11, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-22", "10:00", "10:30", 0.0, "702", "bsb", -1, False, False, -1], [14, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-22", "17:30", "18:00", 0.0, "702", "bsb", -1, False, False, -1]]

    res_requests = IntervalTree()
    for res in event:
        hour_start_mod = float(f'{res[4][:2]}') if res[4][3:] == '00' else float(f'{res[4][:2]}.5')
        hour_end_mod = float(f'{res[5][:2]}') if res[5][3:] == '00' else float(f'{res[5][:2]}.5')
        res_requests[hour_start_mod:hour_end_mod] = res[1]
   
    print(res_requests)
     for res in resources:
        print('new')
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
                print(available_hours.envelop(hour_start, hour_end))
                print(f'{hour_start}   {hour_end}')
                lock = True
            if (h['places_available'] == 1) and (lock == True):
                hour_start = h['hour']
                hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 
                lock = False
            if (i == (len(res['hours']) - 1)) and (lock == False):
                hour_end = '18'
                hour_end = float(f'{hour_end}')
                print(available_hours.envelop(hour_start, hour_end))
                print(f'{hour_start}   {hour_end}')
                lock = False

    v0 = '00000'
    v1 = 'antoine2.salamitou@outlook.fr'
    v2 = '2020-10-18'
    v3 = '10:00'
    v4 = None
    v5 = None
    v6 = '0'
    v7 = '702'
    v8 = 'bsb'
    '''
    rds_host  = 'afflubot.chmploavcitj.eu-west-3.rds.amazonaws.com'
    rds_username = 'afflubot'
    rds_user_pwd = 'afflubot828378YH029'
    rds_db_name = 'postgres'
    conn_string = "host=%s user=%s password=%s dbname=%s" % \
                    (rds_host, rds_username, rds_user_pwd, rds_db_name)
    print(conn_string)
    conn = psycopg2.connect(conn_string)
    print('12:30' >= '20:00')
    print('15:00' <= '10:00')

    cursor = conn.cursor()
    email = "antoine.salamitou@outlook.fr"
    date = '2020-10-23'
    heure_debut_request = '10:00'
    heure_fin_request = '20:00'
    #cursor.execute(""" CREATE TABLE demandes_reservations (id SERIAL, email varchar(400) NOT NULL, auth_token varchar(400), date DATE NOT NULL,  heure_debut varchar(400) NOT NULL, heure_fin varchar(400), valide float NOT NULL, type varchar(400), etablissement varchar(400), etage_pref int DEFAULT -1, etage_pref_mandatory boolean default False, morcelle boolean default False, morcelle_h_already_taken int default -1); """)
    cursor.execute(f"Select * from demandes_reservations") 
    #cursor.execute(f"Select * from demandes_reservations where date = current_date + INTERVAL '2 DAY' and valide = 0 and heure_debut::time >  '10:00'::time and type='702'") 
    #cursor.execute(f"delete from demandes_reservations;") 
    raw = cursor.fetchall()

    print(raw)
    conn.commit()
    cursor.close()
    conn.close()
    '''v0 = 'antoine.salamitou@outlook.fr'
    v1 = '1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662'
    v5 = 0
    v6 = '702'
    v7 = 'bsb'
    v8 = -1
    array = ['2020-10-23']
    array2 = [
 
        [
            ['14:00', '18:00'], ['11:00', '11:30'], ['11:30', '14:00'], ['10:30', '17:30']
        ]
    ]
    v9 = False
    v10 = False
    v11 = -1
    
    for idx, v2 in enumerate(array):
        for j in array2[idx]:
            v3 = j[0]
            v4 = j[1]
            cursor.execute("INSERT INTO demandes_reservations (email,auth_token, date, heure_debut, heure_fin, valide, type, etablissement, etage_pref, etage_pref_mandatory, morcelle, morcelle_h_already_taken) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11))
    

    raw = cursor.fetchall()

    print(raw)
    conn.commit()
    cursor.close()
    conn.close()

    
    
    conn.commit()
    cursor.close()
    conn.close()
    print(raw)
    a = [[6, "antoine.salamitou@outlook.fr", "1aa436a87063998011d15f60ca489b3bf045275601c08ae3ce262ab4b3480662", "2020-10-20", "11:00", "18:00", 0.0, "702", "bsb", -1, False, False, -1]]
    for res in a:
            print(f'searching for {res[1]} from {res[4]} to {res[5]}')

            key0 = f'0/{res[4]}/{res[5]}'
            key1 = f'1/{res[4]}/{res[5]}'
            key2 = f'2/{res[4]}/{res[5]}'
            key3 = f'3/{res[4]}/{res[5]}'
        
    print(datetime.now() + timedelta(days=2))
    #print(json.dumps(raw, default=str))
    #now = datetime.datetime.now()
    #print(now.hour)
    hour_start = '09:30'
    date = '2020-10-20'
    resa_link = 'https://reservation.affluences.com/api/resources/'
    res_name = {'bsb': 'ba970374-77b3-4619-af1f-020ee44dcfc0'}
    r = requests.get(f'{resa_link}ba970374-77b3-4619-af1f-020ee44dcfc0/available?date={date}&type=702&start_hour={hour_start}')
    resources = json.loads(r.content)
    available_hours = IntervalTree()
    #to do with floor here
    for res in resources:
        if len(res['hours']) == 0:
            break
        etage = res['resource_name'][-3]
        lock = False
        for i, h in enumerate(res['hours']):
            if i == 0:
                hour_start = h['hour']
                hour_start = float(f'{etage}{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{etage}{hour_start[:2]}.5') 
                print(hour_start)
            if (h['places_available'] == 0) and (lock == False):
                hour_end = h['hour']
                hour_end = float(f'{etage}{hour_end[:2]}') if hour_end[3:] == '00' else float(f'{etage}{hour_end[:2]}.5') 
                available_hours[hour_start:hour_end] = res['resource_id']
                lock = True
            if (h['places_available'] == 1) and (lock == True):
                hour_start = h['hour']
                hour_start = float(f'{etage}{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{etage}{hour_start[:2]}.5') 

                lock = False
            if (i == (len(res['hours']) - 1)) and (lock == False):
                hour_end = '18'
                hour_end = float(f'{etage}{hour_end}')
                available_hours[hour_start:hour_end] = res['resource_id']
                lock = False
        
    for res in resources:
        if len(res['hours']) == 0:
            break
        etage = res['resource_name'][-3]
        lock = False
        for i, h in enumerate(res['hours']):
            if i == 0:
                hour_start = h['hour']
                hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 
                print(hour_start)
            if (h['places_available'] == 0) and (lock == False):
                hour_end = h['hour']
                hour_end = float(f'{hour_end[:2]}') if hour_end[3:] == '00' else float(f'{hour_end[:2]}.5') 
                available_hours[hour_start:hour_end] = res['resource_id']
                lock = True
            if (h['places_available'] == 1) and (lock == True):
                hour_start = h['hour']
                hour_start = float(f'{hour_start[:2]}') if hour_start[3:] == '00' else float(f'{hour_start[:2]}.5') 

                lock = False
            if (i == (len(res['hours']) - 1)) and (lock == False):
                hour_end = '18'
                hour_end = float(f'{hour_end}')
                available_hours[hour_start:hour_end] = res['resource_id']
                lock = False
    now = datetime.datetime.now()
    print(available_hours)
    #hour_start = f'{res[4][:2]}' if res[4][3:] == '00' else f'{res[4][:2]}.5'
    #hour_end = f'{res[5][:2]}' if res[5][3:] == '00' else f'{res[5][:2]}.5'
    available_for_this_res = set()
    #for loop
    hour_start = '13:00'
    hour_end = '13:30'
    hour_start = f'{hour_start[:2]}' if hour_start[3:] == '00' else f'{hour_start[:2]}.5'
    hour_end = f'{hour_end[:2]}' if hour_end[3:] == '00' else f'{hour_end[:2]}.5'
    
    if len(available_for_this_res) == 0:
        available_for_this_res = available_hours.overlaps(hour_start,hour_end)
    
    resource_to_reserve = available_for_this_res.pop()
    available_hours.remove(Interval(resource_to_reserve.begin, resource_to_reserve.end, resource_to_reserve.data))
    reserve(this_res)


    #print(r.content)
    
    for line in raw:
        heure_debut = line[4]
        heure_fin = line[5]
        if (heure_debut <= heure_debut_request) or (heure_fin >= heure_fin_request):
            return ...
    

    #raw.sort(key=lambda tup: tup[1])
    #print(raw)
    #cursor.execute("""select *  FROM demandes_reservations where;""")
    #raw = cursor.fetchall()
    #for line in raw:
    #   print(line)
    #cursor.execute("""ALTER TABLE demandes_reservations ADD COLUMN time_resa int;""")
    #cursor.execute(""" DROP TABLE demandes_reservations; """)
    #cursor.execute(""" CREATE TABLE demandes_reservations (id SERIAL, email varchar(400) NOT NULL, auth_token varchar(400), date DATE NOT NULL,  heure_debut varchar(400) NOT NULL, heure_fin varchar(400), valide float NOT NULL, type varchar(400), etablissement varchar(400), etage_pref int DEFAULT -1, etage_pref_mandatory boolean default False, morcelle boolean default False, morcelle_h_already_taken int default -1); """)
    time_start = '10:00'
    date = '2020-10-16' 
    time_end='20:00'
    #cursor.execute("INSERT INTO demandes_reservations (email,auth_token, date, heure_debut, heure_fin, time_resa, valide, type, etablissement) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (v1, v0, v2, v3, v4, v5, v6, v7, v8))

    #cursor.execute(f"UPDATE demandes_reservations SET valide = -2 where email='{email}' and heure_debut='{time_start}' and heure_fin = '{time_end}' and date = '{date}'::date")
    conn.commit()
    cursor.close()
    conn.close()
   


    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('bsb_users')
    result = table.query(
        KeyConditionExpression=Key('user_email').eq('antoine.salamitou@outlook.fr')
    )
    print(result)
    #api_key = 'c03628ad-7301-4577-b6bb-153cc75951a9'
    #print('implement if api_key does not work ask for one')
    ##url = 'https://reservation.affluences.com/api/myreservations/token'
    #headers = {'Content-type': 'application/json', 'host': 'reservation.affluences.com', 'user-identifier': 'c03628ad-7301-4577-b6bb-153cc75951a9'}
    #myobj = {"email": 'antoine@antoine.fr' }
    #r = requests.post(url, data=json.dumps(myobj), headers=headers) 
    #r_json = json.loads(r.content)['error'] == 'not_found'
    #print(r_json)
    #print(url)
    #print(headers)
    #print(myobj)
    email = 'antoine.salamitou@outlook.fr'
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('bsb_users')
    result = table.query(
        KeyConditionExpression=Key('user_email').eq(email)
    )
    print(result['Items'][0]['auth_token'])

    print('auth_token93U39U39'[0:10])
    print('auth_token93U39U39'[10:])
    TO DO : ERROR IF NOT GOOD MAIL HERE 
    {
    "error": "email_requirements_do_not_match",
    "errorMessage": "Veuillez renseigner l’adresse email utilisée lors de l’inscription à la bibliothèque Sainte-Barbe.\nLa liste des nouveaux inscrits est mise à jour à minuit.\nEn cas de questions veuillez contacter la bibliothèque Sainte-Barbe.",
    "showMessage": True
    }

    TO DO IF RESA DONNE CA => ALERTER MOI L'API KEY MARCHE PLUS 
    {
    "reservation_id": 3551946,
    "auth_token": None,
    "user_validation": True,
    "success": "reservation_confirm_request_send",
    "successMessage": "Votre demande de réservation a bien été prise en compte, vous devez la confirmer depuis le mail que nous venons de vous envoyer. Pour rappel, l'adresse mail que vous avez utilisée est antoine.salamitou@outlook.fr.",
    "cancellation_token": None
    }
    TO DO
    if send token renvoie ca => skip l'identif pour tout et empecher le report de place qui marchera pas (on aura pas acces aux places ni au cancel token) + envoi de mail a moi
    {
    "error": "internal_error",
    "errorMessage": "Erreur lors du traitement de votre requête. Veuillez réessayer plus tard.",
    "showMessage": True
    }
    TO RECUPERER 2/3 CLEFS API POUR POUVOIR REMPLACER AU CAS OU
    RENVOYER TAILLE AUTHTOKEN 000000000000 si pas bon pour que le front sache quand c ok
    quand c ok => proposer option annuler, quand c pas ok et qu'il y a une nouvelle connexion, voir si on peut
    enregistrer 5mn par 5 mn toutes les dispos pour chaque table (dynamo)
    penser a faire un timer de 30s, histoire de se lancer a 10h30 +30s quand les inscriptions sont terminees voir les resultats
    proposer un truc en plus : etage 0/1/2 ou 3 obligatoire oui ou non, proposer option morceller les horaires si possible avec annulation (si auth token != 0000)
    enregistrer le auth token dans la demande de resa :
    annuler 
    quand on reserve une place, penser au cas ou email non valdie (voir erreur plus haut)
    base de donnée effective jointe avec demande sur index, avec cancellation token et les autres infos  + delete True ou False (si remplacee)
    lambda qui query la db avec les demandes de resa jointe avec les resa de la seconde table (joindre sur index) >= heure actuelle en donnant en entree toutes les demandes avec leur validation code et qui appelle une autre lambda qui va envoyer les requests
    query toutes les dispos de la journée => table de hachage avec comme entree l'heure debut l'heure fin
    pour chaque demande de resa, hacher heure de rentrer et heure de fin => chercher si ca existe et balancer une request asynchrone et continuer
    si ca existe pas dans un second temps, et si l'utilisateur a dit ok chercher les dispos morcellées en 2 UNIQUEMENT EN 2 (AVEC + OU MOINS 1) si auth token est ok => mais faire valider la premiere, puis quand la premiere est validée, faire la deuxieme, etc ... et dire a la table des resa ou on va rajouter une col : x premiere h validees
    une fois que tout est bon, renvoyer tout ca a une autre lambda qui va modifier les demandes de resa dans la postgre
    pour rendre les trucs optionnels : hacher etage (0/1/2/3) + heure_debut + heure_fin et ca va chercher les 4, avec la preference en premier, puis 2 puis 3 si user a dit ok
    
    
    step 00.5 : TO DO TO TEST quand debut de la resa deja commencée, reserve a partir de mtn
    step 0: limiter le nb de gens par creneau
    step 1: morceler : créer les morcellement a 10H35 le jour meme et supprimer l'ancienne
    step 2: enregistrer 5 mn par 5 mn les differentes dispos dans s3 
    faire step functions pour bsg 
    
    changer les + 1 +2 heure a heure d'été heure d'iver
    step 0.1 verifiez algo prend bien plus grande dispo dabord
    step 0.5: if no request res => stop step function
    step 0 : if ajr : time > time actuel, if 2morow time > 10:00::time 
    step 5 error queue
    step 7 : changer front avec options, changer la hach avec l'etage + implementer fonction annule deux resa d'un coup pour en faire une troisieme 
    step 8: avec auth token verifier que la resa a bien été validée une h apres
    UNIQUEMENT SI FINI AU DESSUS cas etage prefere + cas annulation (dans le cas ou on est valide = 2, avec preference) si auth token non nul  + morceler
    cancel_token = "e2612eb5-e97f-54d9-9c0a-7f45d6475774"
    date = '2020-10-19'
    email = "antoine.salamitou@outlook.fr"
    start_hour = '11:00'
    stop_hour = '11:30'
    ressource_id = '8219'
    response = requests.delete(
        f'https://reservation.affluences.com/api/cancelReservation/?email_token={cancel_token}'
    )
    print(response)
    if response.status_code == 200:
        #while response code not ok... change end_time with duration
        url = f'https://reservation.affluences.com/api/reserve/{ressource_id}'
        myobj = {"date": date,
                "email": email,
                "end_time": stop_hour,
                "note": None,
                "person_count": None,
                "start_time": start_hour,
                "user_firstname": None,
                "user_lastname": None,
                "user_phone": None}
        headers = {'Content-type': 'application/json', 'user-identifier': 'c03628ad-7301-4577-b6bb-153cc75951a9'}
        x = requests.post(url, data=json.dumps(myobj), headers=headers)
        print(x)
    else:
        print('delete error')
    
    '''
