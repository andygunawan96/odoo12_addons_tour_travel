from odoo import fields,api,models
import json,traceback,logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtCustomerParentBookerRel(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.parent.booker.rel'
    _rec_name = 'display_name'
    _description = 'Tour & Travel - Customer Parent Booker Rel'

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', required=True)
    customer_id = fields.Many2one('tt.customer', 'Customer', required=True, domain="[('customer_parent_ids', '=', customer_parent_id)]")
    display_name = fields.Char('Display Name', compute='_compute_display_name')
    job_position_id = fields.Many2one('tt.customer.job.position', 'Job Position', domain="[('customer_parent_id', '=', customer_parent_id)]")

    @api.depends('customer_parent_id', 'customer_id')
    @api.onchange('customer_parent_id', 'customer_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%s)' % (rec.customer_id.name, rec.customer_parent_id.name)
