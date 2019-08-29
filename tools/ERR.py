import json
from .api import Response
from .db_connector import BackendConnector as db_con


ERR_CODE = {}


def _do_config():
    _db_con = db_con()
    data = _db_con.get_error_code_api()['response']
    if data:
        [ERR_CODE.update({int(key): val}) for key, val in data.items()]
    return True


def _get_error_data(_error_code):
    if not ERR_CODE:
        _do_config()

    res = ERR_CODE.get(_error_code, {'code': -1, 'message': ''})
    return res


def get_message(_error_code, parameter='', additional_message=''):
    _data = _get_error_data(_error_code)

    message = _data['message']
    if parameter:
        message = message % parameter
    if additional_message:
        message = '%s, %s' % (message, additional_message)

    return message


def get_error(_error_code=500, parameter='', additional_message=''):
    _data = _get_error_data(_error_code)

    message = _data['message']
    if parameter:
        message = message % parameter
    if additional_message:
        message = '%s, %s' % (message, additional_message)

    res = Response().get_error(message, _data['code'])
    return res


def get_no_error(response=''):
    res = Response().get_no_error(response)
    return res


class RequestException(Exception):
    def __init__(self, code):
        err_dict = get_error(code)
        self.code = err_dict['error_code']
        self.message = err_dict['error_msg']
        super(RequestException, self).__init__(err_dict['error_msg'])

    def __str__(self):
        return 'Code = %s , Message = %s' % (self.code, self.message)

    def error_dict(self):
        return {'error_code': self.code, 'error_msg': self.message, 'response':''}
