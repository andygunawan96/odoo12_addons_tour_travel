from odoo import api, fields, models, _
import logging, traceback
import requests
import json

_logger = logging.getLogger(__name__)

class TtAccountingQueue(models.Model):
    _name = 'tt.accounting.queue'
    _inherit = 'tt.history'
    _description = 'Accounting Queue'
    _order = 'id DESC'

    request = fields.Text('Request', readonly=True)
    response = fields.Text('Response', readonly=True)
    transport_type = fields.Char('Transport Type', readonly=True)
    res_model = fields.Char('Model', readonly=True)
    state = fields.Selection([('new', 'New'), ('success', 'Success'), ('failed', 'Failed')], 'State', default='new', readonly=True)
    send_uid = fields.Many2one('res.users', 'Last Sent By', readonly=True)
    send_date = fields.Datetime('Last Sent Date', readonly=True)
    action = fields.Char('Action', readonly=True)

    def to_dict(self):
        return {
            'request': self.request,
            'transport_type': self.transport_type,
            'action': self.action,
            'res_model': self.res_model,
            'state': self.state
        }

    def action_send_to_jasaweb(self):
        try:
            self.send_uid = self.env.user.id
            self.send_date = fields.Datetime.now()
            res = self.env['tt.accounting.connector'].add_sales_order(self.request)
            if res.get('status_code') == 200:
                self.state = 'success'
            else:
                self.state = 'failed'
            if res.get('content'):
                try:
                    res.update({
                        'content': res['content'].decode("UTF-8")
                    })
                except (UnicodeDecodeError, AttributeError):
                    pass
            self.response = json.dumps(res)
        except Exception as e:
            _logger.error(traceback.format_exc())
