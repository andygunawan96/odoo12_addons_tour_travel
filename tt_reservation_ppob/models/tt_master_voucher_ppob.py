from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables, util
from datetime import datetime
import json, logging

_logger = logging.getLogger(__name__)
voucher_types = [
    ('prepaid_mobile', 'Prepaid Mobile'),
    ('game', 'Game Voucher'),
    ('others', 'Others')
]


class TtMasterVoucherPPOB(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.master.voucher.ppob'
    _rec_name = 'display_name'
    _order = 'sequence'
    _description = 'Master Voucher PPOB'

    name = fields.Char('Operator Name', default='Unnamed')
    code = fields.Char('Code', default='')
    value = fields.Integer('Nominal', default=0)
    type = fields.Selection(voucher_types, 'Voucher Type', default='prepaid_mobile')

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_ppob.tt_provider_type_ppob').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    sequence = fields.Integer('Sequence', default=50)
    display_name = fields.Char('Display Name', compute='_compute_display_name')
    active = fields.Boolean('Active', default=True)

    @api.depends('name', 'value')
    @api.onchange('name', 'value')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name + ' - ' + util.get_rupiah(rec.value)
