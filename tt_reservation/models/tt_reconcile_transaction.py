from odoo import api,fields,models
from datetime import datetime
from odoo.exceptions import UserError

class TtReconcileTransaction(models.Model):
    _name = 'tt.reconcile.transaction'
    _description = 'Rodex Model Reconcile'
    _rec_name = 'display_reconcile_name'
    _order = 'provider_type_id,provider_id,transaction_date desc'

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

    def compare_reconcile_data(self):
        for rec in self.reconcile_lines_ids.filtered(lambda x: x.state == 'not_match'):
            found_rec = self.env['tt.reservation.%s' % (self.provider_type_id.code)].search([('pnr','=',rec.pnr),
                                                                                 ('total_nta','=',rec.total)],limit=1)
            if found_rec:
                rec.write({
                    'res_model': found_rec._name,
                    'res_id': found_rec.id,
                    'state': 'match'
                })

    def view_filter_tree(self):
        tree_id = self.env.ref('tt_reservation.tt_reconcile_transaction_lines_tree_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issued Reconcile Line(s)',
            'res_model': 'tt.reconcile.transaction.lines',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': tree_id.id,
            'context': {},
            'domain': [('reconcile_transaction_id', '=', self.id)],
            'target': 'current',
        }

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
    currency_id = fields.Many2one('res.currency','Currency',default=lambda self: self.env.user.company_id.currency_id, readonly=True)
    vendor_start_balance = fields.Monetary('Vendor Start Balance', readonly=True)
    vendor_end_balance = fields.Monetary('Vendor End Balance', readonly=True)
    ticket_numbers = fields.Text('Ticket')
    description = fields.Text('Description')

    state = fields.Selection([('match','Match'),
                              ('not_match','Not Match'),
                              ('done','Done'),
                              ('ignore','Ignore')],'State')
    res_model = fields.Char('Ref Model', readonly=True)
    res_id = fields.Char('Ref ID', readonly=True)

    def ignore_recon_line_from_button(self):
        if self.state == 'not_match':
            self.state = 'ignore'
        else:
            raise UserError('Can only ignore [Not Match] state.')

    def unignore_recon_line_from_button(self):
        if self.state == 'ignore':
            self.state = 'not_match'
        else:
            raise UserError('Can only unignore [ignore] state.')