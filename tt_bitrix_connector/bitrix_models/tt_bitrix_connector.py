import json
import logging
import urllib
from ...tools import util
import odoo.tools as tools
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GlobalCredentials():
    _config = {
        'bitrix_url': 'https://bitrix.skytors.id/rest/',
        'user_id': '97/',
        'code': '602enlcgh0len65z/',
        'back_url': tools.config.get('backend_url','')
    }

    def get_config(self):
        return self._config


class BitrixContact(dict):
    cred = GlobalCredentials()
    _config = cred.get_config()

    def __init__(self, seq=None, **kwargs):
        for k in kwargs.keys():
            if k in self:
                self[k] = kwargs[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        if name in self:
            self[name] = value
        else:
            raise AttributeError("No such attribute: " + name)

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def _get_url(self, param):
        return self._config['bitrix_url'] + param + '?auth=' + self._get_token()

    def _get_web_hook(self, param):
        return self._config['bitrix_url'] + self._config['user_id'] + self._config['code'] + param

    def GetContacts(self):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('crm.contact.list'), data={}, headers=headers, method='POST', content_type='data', request_type='', timeout=120)
        return res

    def SelectContact(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('crm.contact.list'), data=vals, headers=headers, method='POST', content_type='data', request_type='json', timeout=120)
        return res

    def AddContact(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('crm.contact.add'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def UpdateContact(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('crm.contact.update'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def DeleteContact(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('crm.contact.delete'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def NotifyWallPost(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('log.blogpost.add'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res


class BitrixTasks(dict):
    cred = GlobalCredentials()
    _config = cred.get_config()

    def __init__(self, seq=None, **kwargs):
        for k in kwargs.keys():
            if k in self:
                self[k] = kwargs[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        if name in self:
            self[name] = value
        else:
            raise AttributeError("No such attribute: " + name)

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def _get_url(self, param):
        return self._config['bitrix_url'] + param + '?auth=' + self._get_token()

    def _get_web_hook(self, param):
        return self._config['bitrix_url'] + self._config['user_id'] + \
               self._config['code'] + param

    def AddTask(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('task.item.add'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def UpdateTask(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('task.item.update'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def DeleteTask(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('task.item.delete'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def SelectTask(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('task.item.list'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res

    def NotifyWallPost(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('log.blogpost.add'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res


class BitrixUsers(dict):
    cred = GlobalCredentials()
    _config = cred.get_config()

    def __init__(self, seq=None, **kwargs):
        for k in kwargs.keys():
            if k in self:
                self[k] = kwargs[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        if name in self:
            self[name] = value
        else:
            raise AttributeError("No such attribute: " + name)

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def _get_url(self, param):
        return self._config['bitrix_url'] + param + '?auth=' + self._get_token()

    def _get_web_hook(self, param):
        return self._config['bitrix_url'] + self._config['user_id'] + self._config['code'] + param

    def SelectUser(self, vals):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        res = util.send_request(self._get_web_hook('user.get'), data=vals, headers=headers, method='POST', content_type='json', request_type='json', timeout=120)
        return res
