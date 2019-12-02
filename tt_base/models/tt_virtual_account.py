from odoo import api, fields, models
from ...tools.api import Response
import traceback,logging
from ...tools import ERR
import json

_logger = logging.getLogger(__name__)

class VirtualAccount(models.Model):
    _name = 'tt.virtual.account'
    _description = 'Rodextrip Virtual Account'
    # _rec_name = 'Virtual Account'

    seq_id = fields.Char('Sequence Code', index=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    bank_id = fields.Many2one('tt.bank', 'Bank', readonly=True)
    virtual_account_number = fields.Char('Virtual Account Number')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.virtual.account')
        return super(VirtualAccount, self).create(vals_list)