import base64

import pytz

from .api import Response
from datetime import datetime, timedelta
import logging,traceback
import copy
import json
import requests
import unicodedata
import re

_logger = logging.getLogger(__name__)
TIMEOUT = 30
CACHE_TIME = 300


def _default_headers(data=None):
    data = data and data or {}
    res = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'python-requests/2.18.4',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
    }
    res.update(data)
    return res

def encode_authorization(_id, _username, _password):
    credential = '%s:%s:%s' % (_id, _username, _password)
    res = base64.b64encode(credential.encode())
    return res


def decode_authorization(_code):
    credential = base64.b64decode(_code).decode()
    cred = credential.split(':')
    if len(cred) != 3:
        # May 6, 2019 - SAM
        # Update return dict kosong apabila tidak berhasil decode
        # Digunakan saat DbConnector melakukan config
        return {}
        # raise Exception('Authorization is not valid')
    res = {
        'uid': int(cred[0]),
        'username': cred[1],
        'password': cred[2],
    }
    return res


def get_request_data(request):
    host_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '')
    if not host_ip:
        host_ip = request.httprequest.environ.get('REMOTE_ADDR', '')

    res = {
        'host_ip': host_ip,
        'data': request.jsonrequest,
        'sid': request.session.sid,
        'action': request.httprequest.environ.get('HTTP_ACTION', False),
    }
    return res


def pop_empty_key(data,whitelist = []):
    temp_key = [key for key,value in data.items() if not value and key not in whitelist]

    for key in temp_key:
        data.pop(key)


def get_without_empty(dict,key,else_param=False):
    if key in dict:
        value = dict[key]
        if value not in [0,'',None]:
            return value
    return else_param

def send_request(url, data=None, headers=None, method=None, cookie=None, content_type='json', request_type='', timeout=TIMEOUT):
    '''
        :param url:
        :param data:
        :param headers:
        :param method:
        :param cookie:
        :param content_type:
            'json': response.json()
            'text': response.text()
            'content': response.content() --> asumsi bytes apabila bytes akan di base64 encode
        :param timeout:
        :return:
    '''
    ses = requests.Session()
    cookie and [ses.cookies.set(key, val) for key, val in cookie.items()]

    data = data and data or {}
    is_data_dict = True if type(data) == dict else False
    headers = headers and headers or _default_headers()
    if not method:
        method = data and 'POST' or 'GET'
    if not request_type:
        request_type = 'json' if is_data_dict else 'data'
    if method == 'GET' and data and is_data_dict:
        addons = ''
        temp = ['%s=%s' % (key, val) for key, val in data.items()]
        # August 30, 2019 - SAM
        # FIXME comment untuk sementara karena ada error pada hotel
        # if url[-1] != '/':
        #     addons += '/'
        if url.find('?') < 0:
            addons += '?'
        addons = '%s%s' % (addons, '&'.join(temp))
        url = '%s%s' % (url, addons)

    response = None
    param = {
        'url': url,
        'headers': headers,
        'timeout': timeout,
    }
    if method != 'GET' and data:
        if request_type == 'json':
            param['json'] = data
        else:
            param['data'] = data

    req_obj = getattr(ses, method.lower(), None)
    if not req_obj:
        raise Exception('Method not Found')

    try:
        response = req_obj(**param)
        response.raise_for_status()
        values = {'error_code': 0}
    except Exception as e:
        values = {
            'error_code': 500,
            'error_msg': str(e),
        }

    try:
        if content_type == 'json':
            content = response.json()
        elif content_type == 'content':
            content = base64.b64encode(getattr(response, 'content', b'')).decode()
        else:
            content = getattr(response, 'text', '')
    except Exception as e:
        _logger.error('Error util send request, %s' % traceback.format_exc())
        content = getattr(response, 'text', '')

    values.update({
        'http_code': getattr(response, 'status_code', ''),
        'response': content,
        'url': url,
        'cookies': response.cookies.get_dict() if getattr(response, 'cookies', '') else ''
    })
    res = Response(values).to_dict()
    return res

# def send_request(url, data=None, headers=None, method=None, cookie=None, is_json=False, timeout=TIMEOUT):
#     ses = requests.Session()
#     cookie and [ses.cookies.set(key, val) for key, val in cookie.iteritems()]
#
#     data = data and data or {}
#     headers = headers and headers or _default_headers()
#     if not method:
#         method = data and 'POST' or 'GET'
#     response = None
#     try:
#         if method == 'GET':
#             addons = ''
#             if data and type(data) == dict:
#                 temp = ['%s=%s' % (key, val) for key, val in data.items()]
#                 # August 30, 2019 - SAM
#                 # FIXME comment untuk sementara karena ada error pada hotel
#                 # if url[-1] != '/':
#                 #     addons += '/'
#                 if url.find('?') < 0:
#                     addons += '?'
#                 addons = '%s%s' % (addons, '&'.join(temp))
#             url = '%s%s' % (url, addons)
#             response = ses.get(url=url, headers=headers, timeout=timeout)
#         elif method == 'POST' and type(data) == dict:
#             response = ses.post(url=url, headers=headers, json=data, timeout=timeout)
#         elif method == 'PUT' and type(data) == dict:
#             response = ses.put(url=url, headers=headers, json=data, timeout=timeout)
#         else:
#             response = ses.post(url=url, headers=headers, data=data, timeout=timeout)
#         response.raise_for_status()
#         values = {'error_code': 0}
#     except Exception as e:
#         values = {
#             'error_code': 500,
#             'error_msg': str(e),
#         }
#
#     content = response.json() if is_json else getattr(response, 'text', '')
#
#     return content['result']

    # values.update({
    #     'http_code': getattr(response, 'status_code', ''),
    #     'response': content,
    #     'url': url,
    #     'cookies': response.cookies.get_dict() if getattr(response, 'cookies', '') else ''
    # })
    # res = Response(values).to_dict()
    # return res

def vals_cleaner(vals,obj):
    pop_list = []
    for key,value in vals.items():
        if hasattr(obj,key):
            field = getattr(obj,key)
            if obj._fields[key].type == 'many2one':
                field = field.id

            if field == value:
                pop_list.append(key)

    for key in pop_list:
        del vals[key]


def generate_passenger_key_name_1(first_name, last_name, **kwargs):
    key_name = '%s%s' % (first_name, last_name)
    res = key_name.lower().replace(' ', '')
    return res


def generate_passenger_key_name_2(first_name, **kwargs):
    key_name = '%s%s' % (first_name, first_name)
    res = key_name.lower().replace(' ', '')
    return res


def generate_passenger_key_name_3(first_name, last_name, **kwargs):
    key_name = '%s%s' % (last_name, first_name)
    res = key_name.lower().replace(' ', '')
    return res



def match_passenger_data(provider_passengers, passenger_objs):
    psg_obj_data = []
    for psg_obj in passenger_objs:
        psg_val = psg_obj.to_dict()
        key_name_1 = generate_passenger_key_name_1(**psg_val)
        key_name_2 = generate_passenger_key_name_2(**psg_val)
        key_name_3 = generate_passenger_key_name_3(**psg_val)
        psg_val.update({
            'key_name_1': key_name_1,
            'key_name_2': key_name_2,
            'key_name_3': key_name_3,
            'passenger_number': psg_obj.sequence,
            'passenger_id': psg_obj.id,
        })
        psg_obj_data.append(psg_val)

    provider_passenger_temp = []
    for psg in provider_passengers:
        key_name_1 = generate_passenger_key_name_1(**psg)
        key_name_2 = generate_passenger_key_name_2(**psg)
        key_name_3 = generate_passenger_key_name_3(**psg)
        del_idx = -1
        for idx, psg_data in enumerate(psg_obj_data):
            if key_name_1 == psg_data['key_name_1'] or key_name_3 in psg_data['key_name_3'] or key_name_2 == psg_data['key_name_2']:
                del_idx = idx
                psg.update({
                    'passenger_id': psg_data['passenger_id'],
                    'passenger_number': psg_data['passenger_number'],
                })
                break
        if del_idx > -1:
            del psg_obj_data[del_idx]
        else:
            provider_passenger_temp.append(psg)

    if provider_passenger_temp:
        _logger.error('Found unmatch passenger data, total %s' % len(provider_passenger_temp))
        _logger.info('Auto assign passenger id to the unmatch passengers')
        # March 24, 2022 - SAM
        # Membuat mekanisme auto match pax untuk sementara agar tetap terproses
        for psg_idx, psg in enumerate(provider_passenger_temp):
            del_idx = -1
            for psg_data_idx, psg_data in enumerate(psg_obj_data):
                del_idx = psg_data_idx
                psg.update({
                    'passenger_id': psg_data['passenger_id'],
                    'passenger_number': psg_data['passenger_number'],
                })
                break
            if del_idx > -1:
                del psg_obj_data[del_idx]
        # END
    return provider_passengers


def generate_journey_key_name(journey_obj):
    res = '%s%s' % (journey_obj['origin'], journey_obj['destination'])
    return res

def convert_timezone(str_date,origin_tz,dest_tz): ##str_date = '2022-01-18'
    str_date_list = str_date.split('-')
    date_object = datetime(year=int(str_date_list[0]),month=int(str_date_list[1])
                                 ,day=int(str_date_list[2])) #don't construct datetime object with tzinfo, pytz normalize will be off by 7 seconds
    date_aware_object = pytz.timezone(origin_tz).localize(date_object)
    return pytz.timezone(dest_tz).normalize(date_aware_object)

def get_rupiah(price):
    try:
        if price:
            positif = price > -1 and True or False
            temp = abs(int(price))

            temp = str(temp)
            temp = temp.split('-')[-1]
            pj = len(temp)
            priceshow = ''
            for x in range(pj):
                if (pj - x) % 3 == 0 and x != 0:
                    priceshow += ','
                priceshow += temp[x]

            if not positif:
                priceshow = '-' + priceshow
            return priceshow
        else:
            return ''
    except Exception as e:
        return price

def slugify_str(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def get_data_from_list(records, results):
    for rec in records:
        if isinstance(rec, list):
            get_data_from_list(rec, results)
        else:
            results.append(rec)


def get_tree_data(tree_data, keys, is_list=False):
    if not isinstance(keys, list):
        keys = [keys]

    temp_keys = copy.deepcopy(keys)
    data = tree_data
    for key in keys:
        if isinstance(data, dict):
            temp_keys.pop(0)
            if key not in data:
                data = ''
                break
            data = data[key]
        elif isinstance(data, list):
            results = []
            for rec in data:
                result = get_tree_data(rec, temp_keys, is_list)
                if not result:
                    continue
                if isinstance(result, list):
                    get_data_from_list(result, results)
                else:
                    results.append(result)
            data = results
            if len(results) == 1:
                data = results[0]
            break
        else:
            data = ''
            break

    data_text = str(data)
    if is_list:
        if not data_text:
            data = []
        elif not isinstance(data, list):
            data = [data]
    return data

def manage_msg_length(msg_dict,param_msg,add_msg):
    TELEGRAM_MSG_LIMIT = 3800
    if msg_dict['ctr'] not in msg_dict:
        msg_dict[msg_dict['ctr']] = add_msg
    len_msg = len(param_msg)
    len_d_msg = len(msg_dict[msg_dict['ctr']])
    if len_msg + len_d_msg > TELEGRAM_MSG_LIMIT: ## OUT OF BOUND
        ## SPLIT MSG INTO 2, still within limit and leftover passed into recursive
        n_index = param_msg[:TELEGRAM_MSG_LIMIT-len_d_msg].rfind('\n')
        kept_msg = param_msg[:n_index]
        leftover_msg = param_msg[n_index:]
        ##

        msg_dict[msg_dict['ctr']] += kept_msg
        msg_dict['ctr'] += 1
        manage_msg_length(msg_dict,leftover_msg,add_msg) ##send leftover msg to recrursive
    else:
        msg_dict[msg_dict['ctr']] += param_msg
