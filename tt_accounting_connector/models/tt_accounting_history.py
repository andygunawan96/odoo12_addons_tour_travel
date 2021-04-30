from odoo import api, fields, models, _

class TtAccountingHistory(models.Model):
    _name = 'tt.accounting.history'
    _inherit = 'tt.history'
    _description = 'Accounting History'
    _order = 'id DESC'

    request = fields.Text('Request', readonly=True)
    response = fields.Text('Response', readonly=True)
    transport_type = fields.Char('Transport Type', readonly=True)
    res_model = fields.Char('Model', readonly=True)
    state = fields.Selection([('success', 'Success'), ('failed', 'Failed'), ('odoo_failed', 'Failed from Odoo'), ('retried', 'Retried')], 'State', default='success', readonly=True)
    resend_uid = fields.Many2one('res.users', 'Last Resent By', readonly=True)
    resend_date = fields.Datetime('Last Resent Date', readonly=True)

    def action_retry(self):
        self.state = 'retried'
        self.resend_uid = self.env.user.id
        self.resend_date = fields.Datetime.now()
        self.env['tt.accounting.connector'].add_sales_order(self.request)
