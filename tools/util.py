import base64

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
        value = dict['key']
        if value not in [0,'']:
            return value
    return else_param