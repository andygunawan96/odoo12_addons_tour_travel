from odoo import fields,api,models
import json,traceback,logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtOsiCorporateCode(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.osi.corporate.code'
    _rec_name = 'display_name'
    _description = 'Tour & Travel - OSI Corporate Code'

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', required=True)
    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', required=True)
    osi_code = fields.Char('OSI Code', required=True)
    display_name = fields.Char('Display Name', compute='_compute_display_name')

    @api.depends('customer_parent_id', 'carrier_id', 'osi_code')
    @api.onchange('customer_parent_id', 'carrier_id', 'osi_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s (%s)' % (rec.carrier_id.name, rec.osi_code, rec.customer_parent_id.name)
