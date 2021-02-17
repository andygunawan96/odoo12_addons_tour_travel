from odoo import api, fields, models, _
import logging, traceback
from ...tools import variables

_logger = logging.getLogger(__name__)


class MasterTourOtherCharges(models.Model):
    _name = "tt.master.tour.other.charges"
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='')
    pax_type = fields.Selection(variables.PAX_TYPE, string='Pax Type', default='ADT', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount', default=0)
    charge_type = fields.Selection([('FARE', 'FARE'), ('TAX', 'TAX')], string='Charge Type', default='FARE', required=True)
    master_tour_id = fields.Many2one('tt.master.tour', 'Master Tour')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'name': self.name and self.name or '',
            'pax_type': self.pax_type,
            'currency_id': self.currency_id and self.currency_id.name or '',
            'amount': self.amount and self.amount or 0,
            'charge_type': self.charge_type and self.charge_type or ''
        }
