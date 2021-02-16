import json, copy
import logging
from odoo.http import request
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class DestinationToolsV2:
    def __init__(self, provider_type):
        self.provider_type = provider_type
        self.destinations = self.get_and_update_destination_data()

    def validate(self):
        if not self.provider_type:
            err_msg = 'Provider type for destination is mandatory'
            _logger.error(err_msg)
            raise Exception(err_msg)
        return True

    def get_destination_request(self):
        req_data = {
            'provider_type': self.provider_type
        }
        return req_data

    def get_and_update_destination_data(self, force_update=False):
        self.validate()
        res = request.env['tt.destinations'].sudo().get_destination_list_api(self.get_destination_request(), {})
        if res['error_code'] != 0:
            _logger.error('Error Get Pricing Provider Data Backend, %s' % res['error_msg'])
            return {}

        payload = {}
        for rec in res['response']:
            destinations = rec.pop('destinations')
            for dest in destinations:
                code = dest['code']
                dest.update({
                    'country_code': rec['code'],
                    'country_id': rec,
                })
                payload[code] = dest
        return payload

    def get_destination_info(self, code):
        return self.destinations.get(code, {})

    def get_destination_utc_info(self, code):
        obj = self.get_destination_info(code)
        return obj.get('timezone_hour', 0)

    def get_destination_country_code(self, code):
        obj = self.get_destination_info(code)
        if obj and obj.get('country_id'):
            return obj['country_id'].get('code', '')
        return ''
