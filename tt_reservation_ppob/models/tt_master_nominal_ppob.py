from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime
import json, logging

_logger = logging.getLogger(__name__)


class TtMasterNominalPPOB(models.Model):
    _name = 'tt.master.nominal.ppob'
    _rec_name = 'display_name'
    _order = 'nominal'
    _description = 'Rodex Model'

    nominal = fields.Monetary('Nominal')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    display_name = fields.Char('Display Name', compute='_compute_display_name')

    @api.depends('currency_id', 'nominal')
    @api.onchange('currency_id', 'nominal')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.currency_id.name + ' ' + str(rec.nominal)
