from odoo import api, fields, models, _
from odoo.http import request


class ResUsersIp(models.Model):
    _inherit = 'res.users.log'

    http_x_forwarded_for = fields.Char('HTTP X Forwarded For', default='')
    http_client_ip = fields.Char('HTTP Client IP', default='')
    remote_addr = fields.Char('Remote Address', default='')

    def create(self, values):
        values.update({
            'http_x_forwarded_for': request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', ''),
            'http_client_ip': request.httprequest.environ.get('HTTP_CLIENT_IP', ''),
            'remote_addr': request.httprequest.environ.get('REMOTE_ADDR', ''),
        })
        res = super(ResUsersIp, self).create(values)
        return res
