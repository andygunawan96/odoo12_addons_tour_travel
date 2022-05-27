from odoo import fields,api,models
import json,traceback,logging
from datetime import datetime

_logger = logging.getLogger(__name__)

ACCESS_TYPE = [
    ('all', 'ALL'),
    ('allow', 'Allowed'),
    ('restrict', 'Restricted'),
]


class TtCustomerJobHierarchy(models.Model):
    _name = 'tt.customer.job.hierarchy'
    _description = 'Tour & Travel - Customer Job Hierarchy'
    _rec_name = 'sequence'
    _order = 'sequence'

    sequence = fields.Integer('Group Sequence', default=1)
    name = fields.Integer('Name', compute='compute_name', store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent')
    min_approve_amt = fields.Integer('Min Approve Amount', default=1)
    job_position_ids = fields.One2many('tt.customer.job.position', 'hierarchy_id', 'Job Positions')

    @api.onchange('sequence')
    @api.depends('sequence')
    def compute_name(self):
        for rec in self:
            rec.name = rec.sequence or 0


class TtCustomerJobPosition(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.job.position'
    _description = 'Tour & Travel - Customer Job Position'
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent')

    def _get_job_hierarchy_domain(self):
        cus_par_id = self.customer_parent_id and self.customer_parent_id.id or self._context.get('default_customer_parent_id')
        return [('customer_parent_id', '=', cus_par_id)]

    hierarchy_id = fields.Many2one('tt.customer.job.hierarchy', 'Hierarchy Group', required=True, domain=_get_job_hierarchy_domain)
    sequence = fields.Integer('Sequence', default=20)
    is_request_required = fields.Boolean('Issued Request Required', default=True)
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True, help='Only for Airline products.')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_customer_job_position_carrier_rel', 'job_position_id',
                                   'carrier_id', string='Carriers', help='Only for Airline products.')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    max_price = fields.Monetary('Max Price', default=0, help='Put 0 for unlimited max price.')  # sementara global, kalo butuh bisa dibuat sistem rule_ids per provider_type
    max_hotel_stars = fields.Selection([(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], 'Max Hotel Stars', default=5, help='Only for Hotel products.')
    max_cabin_class = fields.Selection([('economy', 'Economy'), ('premium', 'Premium Economy'),
                                        ('business', 'Business Class'), ('first', 'First Class / Executive')], 'Max Cabin Class', default='first', help='Only for Airline and Train products.')

    def get_carrier_code_list(self):
        res = []
        for rec in self.carrier_ids:
            res.append(rec.code)
        return res
