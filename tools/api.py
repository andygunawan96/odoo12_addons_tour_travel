import json


class Response:
    def __init__(self, _data={}):
        self.__dict__ = self._default()
        self.update(_data)

    def _default(self):
        return {
            'error_code': -1,
            'error_msg': '',
            'response': '',
        }

    def update(self, _data):
        self.__dict__.update(_data)

    def to_dict(self):
        return self.__dict__

    def get_no_error(self, response='Success'):
        self.__dict__.update({
            'error_code': 0,
            'response': response
        })
        return self.to_dict()

    def get_error(self, error_message, error_code, additional_message=''):
        self.__dict__.update({
            'error_code': error_code,
            'error_msg': error_message,
            'error_additional_message': additional_message,
            'response': ''
        })
        return self.to_dict()
