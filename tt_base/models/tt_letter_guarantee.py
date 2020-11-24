from odoo import api, fields, models
from datetime import datetime


class TtLetterGuarantee(models.Model):
    _name = 'tt.letter.guarantee'
    _inherit = 'tt.history'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    res_model = fields.Char('Related Reservation Name', index=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource')
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    line_ids = fields.One2many('tt.letter.guarantee.lines', 'lg_id', 'Line(s)', readonly=True, states={'draft': [('readonly', False)]})
    pax_description = fields.Text('Passenger Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    multiplier = fields.Char('Multiplier', default='Pax', required=True, readonly=True, states={'draft': [('readonly', False)]})
    multiplier_amount = fields.Integer('Multiplier Amount', default=0, required=True, readonly=True, states={'draft': [('readonly', False)]})
    quantity_amount = fields.Integer('Quantity Amount', default=0, required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id, readonly=True, states={'draft': [('readonly', False)]})
    price_per_mult = fields.Monetary('Price Per Multiplier', required=True, readonly=True, states={'draft': [('readonly', False)]})
    price = fields.Monetary('Total Price', required=True, readonly=True, states={'draft': [('readonly', False)]})
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('sent', 'Sent'), ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], 'State', default='draft')
    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    sent_date = fields.Datetime('Sent Date', readonly=True)
    sent_uid = fields.Many2one('res.users', 'Sent by', readonly=True)
    paid_date = fields.Datetime('Paid Date', readonly=True)
    paid_uid = fields.Many2one('res.users', 'Paid by', readonly=True)
    cancel_date = fields.Datetime('Cancelled Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled by', readonly=True)

    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('tt.letter.guarantee.seq')
        })
        return super(TtLetterGuarantee, self).create(vals)

    def action_confirm(self):
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })

    def action_sent(self):
        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
        })

    def action_paid(self):
        self.write({
            'state': 'paid',
            'paid_uid': self.env.user.id,
            'paid_date': datetime.now(),
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now(),
        })

    def set_to_draft(self):
        self.write({
            'state': 'draft',
        })


class TtLetterGuaranteeLines(models.Model):
    _name = 'tt.letter.guarantee.lines'
    _description = 'Rodex Model'

    ref_number = fields.Char('Reference Number', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text('Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    lg_id = fields.Many2one('tt.letter.guarantee', 'Letter of Guarantee', required=True, readonly=True, ondelete='cascade')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('sent', 'Sent'), ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], 'State', related='lg_id.state', store=True)
