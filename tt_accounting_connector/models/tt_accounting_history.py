from odoo import api, fields, models, _
from ..accounting_models.tt_accounting_connector import SalesOrder


class TtAccountingHistory(models.Model):
    _name = 'tt.accounting.history'
    _inherit = 'tt.history'
    _description = 'Rodex Model'
    _order = 'id DESC'

    request = fields.Text('Request', readonly=True)
    response = fields.Text('Response', readonly=True)
    transport_type = fields.Char('Transport Type', readonly=True)
    res_model = fields.Char('Model', readonly=True)
    parent_id = fields.Many2one('tt.accounting.history', 'Previous Attempt', readonly=True)
    child_ids = fields.One2many('tt.accounting.history', 'parent_id', 'Retry Attempts')
    state = fields.Selection([('success', 'Success'), ('failed', 'Failed'), ('odoo_failed', 'Failed from Odoo'), ('retried', 'Retried')], 'State', default='success', readonly=True)
    resend_uid = fields.Many2one('res.users', 'Last Resent By', readonly=True)
    resend_date = fields.Datetime('Last Resent Date', readonly=True)

    def action_retry(self):
        self.state = 'retried'
        self.resend_uid = self.env.user.id
        self.resend_date = fields.Datetime.now()
        so = SalesOrder()
        res = so.AddSalesOrder(self.request)
        if res.get('status_code') == 200:
            self.env['tt.accounting.history'].sudo().create({
                'request': self.request,
                'response': res,
                'transport_type': self.transport_type,
                'res_model': self.res_model,
                'state': 'success',
                'parent_id': self.id
            })
        else:
            self.env['tt.accounting.history'].sudo().create({
                'request': self.request,
                'response': 'Failed: ' + str(res),
                'transport_type': self.transport_type,
                'res_model': self.res_model,
                'state': 'failed',
                'parent_id': self.id
            })
