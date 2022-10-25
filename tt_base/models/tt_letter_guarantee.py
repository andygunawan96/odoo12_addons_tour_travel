from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime


class TtLetterGuarantee(models.Model):
    _name = 'tt.letter.guarantee'
    _inherit = 'tt.history'
    _order = 'id DESC'
    _description = 'Letter Guarantee'

    name = fields.Char('Name', required=True, readonly=True)
    res_model = fields.Char('Related Reservation Name', index=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource')
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True, readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([('lg', 'Letter of Guarantee'), ('po', 'Purchase Order')], 'Type', default='lg', required=True, readonly=True, states={'draft': [('readonly', False)]})
    line_ids = fields.One2many('tt.letter.guarantee.lines', 'lg_id', 'Line(s)', readonly=True, states={'draft': [('readonly', False)]})
    parent_ref = fields.Char('Parent Reference', readonly=True, states={'draft': [('readonly', False)]})
    pax_description = fields.Html('Passenger Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    multiplier = fields.Char('Multiplier String', default='Pax', required=True, readonly=True, states={'draft': [('readonly', False)]})
    multiplier_amount = fields.Integer('Multiplier Amount', default=0, required=True, readonly=True, states={'draft': [('readonly', False)]})
    quantity = fields.Char('Quantity String', default='Qty', required=True, readonly=True, states={'draft': [('readonly', False)]})
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
        if vals['type'] == 'po':
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('tt.purchase.order.seq')
            })
        else:
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('tt.letter.guarantee.seq')
            })
        return super(TtLetterGuarantee, self).create(vals)

    def action_confirm(self):
        if not self.env.user.has_group('tt_base.group_lg_po_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })

    def action_sent(self):
        if not self.env.user.has_group('tt_base.group_lg_po_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
        })

    def action_paid(self):
        if not self.env.user.has_group('tt_base.group_lg_po_level_5'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.write({
            'state': 'paid',
            'paid_uid': self.env.user.id,
            'paid_date': datetime.now(),
        })

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_lg_po_level_5'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now(),
        })

    def set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_lg_po_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.write({
            'state': 'draft',
        })

    def open_reference(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class TtLetterGuaranteeLines(models.Model):
    _name = 'tt.letter.guarantee.lines'
    _order = 'id DESC'
    _description = 'Letter Guarantee Lines'

    ref_number = fields.Char('Reference Number', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Html('Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    lg_id = fields.Many2one('tt.letter.guarantee', 'Letter of Guarantee', required=True, readonly=True, ondelete='cascade')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('sent', 'Sent'), ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], 'State', related='lg_id.state', store=True)
