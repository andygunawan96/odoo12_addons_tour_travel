import json
from .api import Response
from odoo.http import request
from .db_connector import BackendConnector

_backendDb = BackendConnector()
ERR_CODE = {}


def _do_config():
    try:
        data = request.env['tt.error.api'].sudo().get_dict_by_int_code()
    except:
        temp = _backendDb.get_error_code_api()
        if temp['error_code'] != 0:
            return False
        data = temp['response']
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

    res = Response().get_error(message, _data['code'], additional_message)
    return res


def get_no_error(response=''):
    res = Response().get_no_error(response)
    return res


class RequestException(Exception):
    def __init__(self, code, additional_message=''):
        add_msg = ', %s' % additional_message if additional_message else ''
        err_dict = get_error(code)
        self.code = err_dict['error_code']
        self.message = '%s%s' % (err_dict['error_msg'], add_msg)
        super(RequestException, self).__init__(err_dict['error_msg'])

    def __str__(self):
        return 'Code = %s , Message = %s' % (self.code, self.message)

    def error_dict(self):
        return {'error_code': self.code, 'error_msg': self.message, 'response':''}
