import logging
import requests

_logger = logging.getLogger(__name__)


class SalesOrder(dict):
    url = 'http://accounting.rodextrip.com'

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

    def AccLogin(self):
        auth = {'usr': 'rodexapi', 'pwd': 'rodexapi'}
        res = requests.post(self.url + '/api/method/login', data=auth)
        _logger.info(res)
        return res

    def GetSalesOrder(self):
        # ses = requests.Session()
        cookies = False
        login_res = self.AccLogin()
        if login_res:
            cookies = login_res.cookies

        headers = {
            'Content-Type': 'application/json, text/javascript, */*; q=0.01',
        }

        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(self.url + '/api/method/jasaweb.rodex', headers=headers, cookies=cookies)
        res = response.content
        return res

    def AddSalesOrder(self, vals):
        # ses = requests.Session()
        cookies = False
        login_res = self.AccLogin()
        if login_res:
            cookies = login_res.cookies

        headers = {
            'Content-Type': 'text/text, */*; q=0.01',
        }

        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(self.url + '/api/method/jasaweb.rodex.insert_journal_entry', data=vals, headers=headers, cookies=cookies)
        if response.status_code == 200:
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')

        res = {
            'status_code': response.status_code,
            'content': response.content
        }
        _logger.info(res)
        return res



