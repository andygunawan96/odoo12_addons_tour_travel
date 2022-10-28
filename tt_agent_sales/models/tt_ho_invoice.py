import traceback

from odoo import models, api, fields, _
from datetime import datetime, timedelta
from odoo import exceptions
from odoo.exceptions import UserError
from ...tools import ERR,util
import base64,logging

_logger = logging.getLogger(__name__)

class Ledger(models.Model):
    _inherit = 'tt.ledger'

    ho_invoice_id = fields.Many2one('tt.ho.invoice','Agent Invoice ID')

class AgentInvoiceInh(models.Model):
    _name = 'tt.ho.invoice'
    _inherit = 'tt.agent.invoice'
    _description = 'HO Invoice'
    _order = 'id desc'

    invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'invoice_id', 'Invoice Line', readonly=True,
                                       states={'draft': [('readonly', False)]})
    payment_ids = fields.One2many('tt.payment.invoice.rel', 'ho_invoice_id', 'Payments',
                                  states={'paid': [('readonly', True)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 readonly=True, states={'draft': [('readonly', False)]},
                                 domain=[('res_model', '=', 'tt.ho.invoice')])
    is_use_credit_limit = fields.Boolean(default=False)

    @api.model
    def create(self, vals_list):
        if type(vals_list) == dict:
            vals_list = [vals_list]
        for rec in vals_list:
            if 'name' not in rec:
                rec['name'] = self.env['ir.sequence'].next_by_code('ho.invoice')
        new_invoice = super(AgentInvoiceInh, self).create(vals_list)
        new_invoice.set_default_billing_to()
        return new_invoice



