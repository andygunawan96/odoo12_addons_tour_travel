from odoo import api,fields,models
from datetime import datetime

class TtReconcileTransaction(models.Model):
    _name = 'tt.reconcile.transaction'
    _description = 'Rodex Model Reconcile'
    _rec_name = 'display_reconcile_name'

    display_reconcile_name = fields.Char('Display Name', compute='_compute_display_reconcile_name',store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='provider_id.provider_type_id', readonly=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True)
    reconcile_lines_ids = fields.One2many('tt.reconcile.transaction.lines','reconcile_transaction_id','Line(s)')
    transaction_date = fields.Date('Transaction Date', readonly=True)
    state = fields.Selection([('open','Open')],'State', default='open', readonly=True)

    @api.depends('provider_id','transaction_date')
    def _compute_display_reconcile_name(self):
        for rec in self:
            rec.display_reconcile_name = '%s %s' % (
                rec.provider_id and rec.provider_id.name or '',
                rec.transaction_date and datetime.strftime(rec.transaction_date,'%Y-%m-%d')
            )

class TtReconcileTransactionLines(models.Model):
    _name = 'tt.reconcile.transaction.lines'
    _description = 'Rodex Model Reconcile Lines'

    reconcile_transaction_id = fields.Many2one('tt.reconcile.transaction','Reconcile Transaction',readonly=True, ondelete='cascade' )
    agent_name = fields.Char('Agent Name',readonly=True)
    pnr = fields.Char('PNR',readonly=True)
    transaction_code = fields.Char('Transaction Code',readonly=True)
    type = fields.Selection([('nta','NTA'),
                             ('insentif','Insentif'),
                             ('top_up','Top Up')],'Type')
    booking_time = fields.Datetime('Booking Time',readonly=True)
    issued_time = fields.Datetime('Issued Time',readonly=True)
    base_price = fields.Monetary('Base Price',readonly=True)
    tax = fields.Monetary('Tax',readonly=True)
    commission = fields.Monetary('Commission',readonly=True)
    total = fields.Monetary('Total Price',readonly=True)
    currency_id = fields.Many2one('res.currency','Currency',default=lambda self: self.env.user.company_id.currency_id)
    vendor_start_balance = fields.Monetary('Vendor Start Balance', readonly=True)
    vendor_end_balance = fields.Monetary('Vendor End Balance', readonly=True)
    ticket_number = fields.Text('Ticket')
    description = fields.Text('Description')
    state = fields.Selection([('match','Match'),
                              ('not_match','Not Match'),
                              ('done','Done')],'State')
