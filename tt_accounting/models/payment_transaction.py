from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    reference = fields.Char('Reference', help='Internal reference of the TX', required=True, index=True,
                            readonly=True, default='New')
    origin = fields.Char('Document Ref.', readonly=True, states={'draft':[('readonly',False)]})
    origin_type = fields.Char('Document Ref. Type', readonly=True, states={'draft':[('readonly',False)]})

    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    agent_id = fields.Many2one('res.partner', string="Agent", readonly=True, states={'draft':[('readonly',False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True)
    sub_agent_id = fields.Many2one('res.partner', string="Sub Agent", readonly=True, states={'draft':[('readonly',False)]})
    sub_agent_type_id = fields.Many2one('tt.agent.type', 'Sub Agent Type', related='sub_agent_id.agent_type_id', readonly=True)

    top_up_id = fields.Many2one('tt.top.up', 'Top Up', readonly=True, states={'draft':[('readonly',False)]})
    ledger_id = fields.Many2one('tt.ledger', 'Ledger', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    reverse_ledger_id = fields.Many2one('tt.ledger', 'Cancelled Ledger', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=True, states={'draft':[('readonly',False)]})
    ho_ledger_id = fields.Many2one('tt.ledger', 'HO Ledger', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def create(self, vals):
        tx = super(PaymentTransaction, self).create(vals)
        tx.reference = self.env['ir.sequence'].next_by_code('payment.transaction')
        return tx

    @api.onchange('agent_id')
    def _onchange_agent_id(self):
        onchange_vals = self.on_change_partner_id(self.agent_id.id).get('value', {})
        self.update(onchange_vals)

    @api.one
    def action_done(self):
        if self.state == 'done':
            raise UserError(_("You cannot Post this transaction which is Done"))

        self.create_ledger()
        self.update({
            'state': 'done',
            'date_validate': fields.Date.today(),
            'validate_uid': self.env.uid,
        })

    @api.one
    def action_unpost(self):
        # self.unlink_ledger()
        if self.ledger_id:
            self.create_reverse_ledger_COR_POR()
        self.update({
            'state': 'authorized',
        })

    @api.one
    def action_cancel(self):
        if self.ledger_id:
            self.create_reverse_ledger_COR_POR()
            # self.unlink_ledger()
        self.update({
            'state': 'cancel',
        })
        if self.top_up_id:
            self.top_up_id.state = 'confirm'
        if self.billing_statement_id:
            self.billing_statement_id.state = 'confirm'

    @api.one
    def action_draft(self):
        self.update({
            'state': 'draft',
        })

    @api.one
    def unlink_ledger(self):
        self.ledger_id.state = 'draft'
        ledger_id = self.ledger_id
        self.ledger_id = False
        ledger_id.sudo().unlink()

    @api.multi
    def unlink(self):
        #TODO : unlink Ledger
        for rec in self:
            if rec.agent_type_id.id in \
                    (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                pass
        res = super(PaymentTransaction, self).unlink()
        pass

    @api.one
    def create_ledger(self):
        if self.origin_type == 'billing': #Billing Statement
            self.create_ledger_COR_POR()

    @api.one
    def create_ledger_COR_POR(self):
        # JUST FOR PARTNER : COR / POR
        ledger = self.env['tt.ledger']
        if self.sub_agent_type_id.id in \
                (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
            name = '%s - %s' % (self.reference, self.origin)
            vals = ledger.prepare_vals('COR/POR Payment : ' + name, name,
                                       self.date_validate, 'inbound',
                                       self.currency_id.id, self.amount + self.fees, 0)
            vals.update({
                'date': fields.Date.context_today(self)
            })
            # vals['refund_id'] = self.id
            vals['agent_id'] = self.sub_agent_id.id
            new_aml = ledger.create(vals)
            new_aml.action_done()
            self.ledger_id = new_aml

    @api.one
    def create_reverse_ledger_COR_POR(self):
        # JUST FOR PARTNER : COR / POR
        ledger = self.env['tt.ledger']
        if self.sub_agent_type_id.id in \
                (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
            vals = ledger.prepare_vals('Cancelled COR/POR Payment : ' + self.reference, self.origin, self.date_validate, 'inbound',
                                       self.currency_id.id, 0, self.amount + self.fees)
            # vals['refund_id'] = self.id
            vals['agent_id'] = self.sub_agent_id.id
            new_aml = ledger.create(vals)
            new_aml.action_done()
            self.reverse_ledger_id = new_aml


    @api.multi
    def _create_ledger_BARU(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            vals = ledger.prepare_vals('Payment : ' + rec.name, rec.name, fields.Datetime.now(), 'payment',
                                       rec.currency_id.id, rec.total_amount, 0)
            vals.update({
                'refund_id': rec.id,
                'agent_id': rec.agent_id.id,
                'transport_type': rec.transaction_type,
                'pnr': rec.pnr
            })

            new_ledger = ledger.create(vals)
            new_ledger.action_done()
            rec.ledger_id = new_ledger
            vals = ledger.prepare_vals('Admin Fee : ' + rec.name, rec.name, fields.Datetime.now(),
                                       'refund.admin.fee', rec.currency_id.id, rec.admin_fee, 0)
            vals['refund_id'] = rec.id
            vals['agent_id'] = self.env['res.partner'].sudo().search([('is_HO', '=', True), ('parent_id', '=', False)],
                                                                     limit=1).id
            vals['transport_type'] = rec.transaction_type
            vals['pnr'] = rec.pnr
            new_ledger = ledger.create(vals)
            new_ledger.action_done()
            rec.ho_ledger_id = new_ledger