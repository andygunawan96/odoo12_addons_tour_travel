from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback
from ...tools.api import Response
import json


class EmailApiCon(models.Model):
    _name = 'email.api.con'
    _inherit = 'tt.api.con'

    def action_call(self, table_obj, action, data, context):
        if action == 'send_email':
            res = table_obj.send_email(data,context)
        else:
            raise RequestException(999)
        return res

    def send_email(self, data, context):
        # Data {'provider_type':'', 'url_booking':'', 'order_number':'',}
        if data.get('provider_type') in ['airline', 'train', 'hotel', 'visa', 'passport', 'activity', 'tour']:
            resv = self.env['tt.reservation.{}'.format(data['provider_type'])].search([('name', '=ilike', data.get('order_number')), ('agent_id', '=', context.get('co_agent_id', -1))], limit=1)
            # TODO: error code ketika object tidak ditemukan
            if resv:
                resv.btb_url = data.get('url_booking', '#')
                template = self.env.ref('tt_reservation_{}.template_mail_{}_issued_{}'.format(data['provider_type'], data.get('type', 'reservation'), data['provider_type'])).id
                mail_mail_obj = self.env['tt.email.queue'].sudo().create({
                    'name': 'Issued ' + resv.name,
                    'type': '{}_{}'.format(data.get('type', 'reservation'), data['provider_type']),
                    'template_id': template,
                    'res_model': resv._name,
                    'res_id': resv.id,
                })
                mail_mail_obj.action_send_email()
                return Response().get_no_error(json.dumps({
                    'mail': mail_mail_obj.name,
                    'failure_reason': mail_mail_obj.failure_reason,
                    'status': mail_mail_obj.active and 'waiting' or 'Done',
                }))
            else:
                raise RequestException(1001)


