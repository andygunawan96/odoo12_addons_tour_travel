import base64
from .api import Response
from datetime import datetime, timedelta
import logging
import copy
import json
import requests

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


def pop_empty_key(data):
    temp_key = [key for key,value in data.items() if not value]

    for key in temp_key:
        data.pop(key)


def get_without_empty(dict,key,else_param=False):
    if key in dict:
        value = dict[key]
        if value not in [0,'']:
            return value
    return else_param


def send_request(url, data=None, headers=None, method=None, cookie=None, is_json=False, timeout=TIMEOUT):
    ses = requests.Session()
    cookie and [ses.cookies.set(key, val) for key, val in cookie.iteritems()]

    data = data and data or {}
    headers = headers and headers or _default_headers()
    if not method:
        method = data and 'POST' or 'GET'
    response = None
    try:
        if method == 'GET':
            addons = ''
            if data and type(data) == dict:
                temp = ['%s=%s' % (key, val) for key, val in data.items()]
                # August 30, 2019 - SAM
                # FIXME comment untuk sementara karena ada error pada hotel
                # if url[-1] != '/':
                #     addons += '/'
                if url.find('?') < 0:
                    addons += '?'
                addons = '%s%s' % (addons, '&'.join(temp))
            url = '%s%s' % (url, addons)
            response = ses.get(url=url, headers=headers, timeout=timeout)
        elif method == 'POST' and type(data) == dict:
            response = ses.post(url=url, headers=headers, json=data, timeout=timeout)
        elif method == 'PUT' and type(data) == dict:
            response = ses.put(url=url, headers=headers, json=data, timeout=timeout)
        else:
            _logger.info("#####################")
            _logger.info(json.dumps(headers))
            _logger.info(json.dumps(data))
            _logger.info(url)
            _logger.info("#####################")
            response = ses.post(url=url, headers=headers, data=data, timeout=timeout)
        response.raise_for_status()
        values = {'error_code': 0}
    except Exception as e:
        values = {
            'error_code': 500,
            'error_msg': str(e),
        }

    content = response.json() if is_json else getattr(response, 'text', '')

    return content['result']

    # values.update({
    #     'http_code': getattr(response, 'status_code', ''),
    #     'response': content,
    #     'url': url,
    #     'cookies': response.cookies.get_dict() if getattr(response, 'cookies', '') else ''
    # })
    # res = Response(values).to_dict()
    # return res