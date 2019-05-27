import os, time, copy
from datetime import datetime, timedelta
import json

PATH_URL = '/var/log/tour_travel/'

# Session Limit in seconds
SESSION_LIMIT = 5 * 60


def _generate_path_folder(_path):
    try:
        folder_list = _path.split('/')
        temp = []
        for rec in folder_list:
            if not rec:
                continue
            n_path = '/%s/%s/' % ('/'.join(temp), rec) if temp else '/%s' % rec
            if not os.path.exists(n_path):
                os.mkdir(n_path)
            temp.append(rec)
        return True
    except:
        return False


def _write_cache(data, path):
    try:
        _file = open(path, 'w')
        _file.write(data)
        _file.close()
        return True
    except Exception as e:
        return False


def _read_cache(path):
    try:
        if not os.path.exists(path):
            return False
        _file = open(path, 'r')
        data = _file.read()
        _file.close()
        return data
    except:
        return False


def _generate_filename(sid, service_name, service_type, extention, is_cache, co_uid=''):
    date_now = datetime.now().strftime('%Y%m%d%H%M%S_') if not is_cache else ''
    filename = '%s%s_%s_%s_%s.%s' % (date_now, sid, service_name, service_type, co_uid, extention)
    if not co_uid:
        filename = '%s%s_%s_%s.%s' % (date_now, sid, service_name, service_type, extention)
    return filename


def _generate_filename_path(host_path, service_name, service_type, extention, is_cache, context):
    if not context:
        raise Exception('Context is not valid')

    path = '%s%s/' % (host_path, context['co_uid'])
    filename = _generate_filename(context['sid'], service_name, service_type, extention, is_cache, context['co_uid'])

    if not os.path.exists(path):
        os.mkdir(path)
    return '%s%s' % (path, filename)


class Session:
    def __init__(self, provider='temp', session_limit=SESSION_LIMIT):
        path_provider = '%s/' % provider.strip() if provider.strip() else ''
        self.session_path = '%s%ssess/' % (PATH_URL, path_provider)
        self.cache_path = '%s%scache/' % (PATH_URL, path_provider)
        self.is_cache = False
        self.session_limit = session_limit
        self.provider = provider
        self._get_config()

    def _get_config(self):
        _generate_path_folder(self.session_path)
        _generate_path_folder(self.cache_path)

    def _get_session_path(self, service_name, service_type, extention, context):
        res = '%s%s' % (self.session_path, _generate_filename(context['sid'], service_name, service_type, extention, self.is_cache))
        return res

    def _get_cache_path(self, service_name, service_type, extention, context):
        res = _generate_filename_path(self.cache_path, service_name, service_type, extention, self.is_cache, context)
        return res

    def write_JSONRequest_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'json', context)
        res = _write_cache(json.dumps(data), _path)
        return res

    def write_JSONResponse_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'json', context)
        res = _write_cache(json.dumps(data), _path)
        return res

    def write_XMLRequest_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'xml', context)
        res = _write_cache(data, _path)
        return res

    def write_XMLResponse_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'xml', context)
        res = _write_cache(data, _path)
        return res

    def write_PDFRequest_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'pdf', context)
        res = _write_cache(data, _path)
        return res

    def write_PDFResponse_cache(self, data, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'pdf', context)
        res = _write_cache(data, _path)
        return res

    def read_JSONRequest_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'json', context)
        res = _read_cache(_path)
        return json.loads(res)

    def read_JSONResponse_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'json', context)
        res = _read_cache(_path)
        return json.loads(res)

    def read_XMLRequest_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'xml', context)
        res = _read_cache(_path)
        return res

    def read_XMLResponse_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'xml', context)
        res = _read_cache(_path)
        return res

    def read_PDFRequest_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'REQ', 'pdf', context)
        res = _read_cache(_path)
        return res

    def read_PDFResponse_cache(self, service_name, context):
        _path = self._get_cache_path(service_name, 'RESP', 'pdf', context)
        res = _read_cache(_path)
        return res

    def _set_expired_time(self, context, session_limit=''):
        data = copy.deepcopy(context)
        if not session_limit:
            session_limit = self.session_limit
        expired_date = datetime.now() + timedelta(seconds=session_limit)
        data.update({'expired_date': expired_date.strftime('%Y-%m-%d %H:%M:%S')})
        return data

    def is_expired(self, context):
        if not context.get('expired_date'):
            return True
        expired_date = datetime.strptime(context['expired_date'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expired_date:
            return True
        return False

    def write_session(self, context):
        data = self._set_expired_time(context)
        _path = self._get_session_path('SignIn', 'SES', 'json', context)
        res = _write_cache(json.dumps(data), _path)
        if not res:
            return res
        return data

    def read_session(self, context):
        _path = self._get_session_path('SignIn', 'SES', 'json', context)
        response = _read_cache(_path)
        if not response:
            return False
        try:
            res = json.loads(response)
            if self.is_expired(res):
                return False
        except:
            return False
        return res

    def update_session(self, context):
        res = self.write_session(context)
        return res


class ClientSession(Session):
    def __init__(self, session_limit=SESSION_LIMIT):
        Session.__init__(self, provider='client_session', session_limit=session_limit)
        self.is_cache = True


class LogConnector(Session):
    def __init__(self, provider, session_limit=SESSION_LIMIT):
        Session.__init__(self, provider=provider, session_limit=session_limit)


class SessionConnector(Session):
    def __init__(self, provider, session_limit=SESSION_LIMIT):
        Session.__init__(self, provider=provider, session_limit=session_limit)
        self.is_cache = True
