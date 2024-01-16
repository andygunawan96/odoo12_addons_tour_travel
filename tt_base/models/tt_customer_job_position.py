from odoo import fields,api,models
import json,traceback,logging
from datetime import datetime

_logger = logging.getLogger(__name__)

ACCESS_TYPE = [
    ('all', 'ALL'),
    ('allow', 'Allowed'),
    ('restrict', 'Restricted'),
]


class TtCustomerJobPosition(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.job.position'
    _description = 'Tour & Travel - Customer Job Position'
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent')
    sequence = fields.Integer('Hierarchy Sequence', default=1)
    min_approve_amt = fields.Integer('Min Approve Amount', default=1)
    is_request_required = fields.Boolean('Issued Request Required', default=True)
    job_rules_ids = fields.One2many('tt.customer.job.rules', 'job_position_id', 'Rules')

    def get_rules_dict(self):
        rules = {}
        for rec in self.job_rules_ids:
            if not rules.get(rec.provider_type_id.code):
                temp_dict = {
                    'currency_code': rec.currency_id.name,
                    'max_price': rec.max_price and rec.max_price or 0
                }
                if rec.provider_type_id.code == 'airline':
                    temp_dict.update({
                        'carrier_access_type': rec.carrier_access_type,
                        'carrier_list': rec.get_carrier_code_list()
                    })
                if rec.provider_type_id.code in ['airline', 'train']:
                    temp_dict.update({
                        'max_cabin_class': rec.max_cabin_class and rec.max_cabin_class or 'first',
                    })
                if rec.provider_type_id.code == 'hotel':
                    temp_dict.update({
                        'max_hotel_stars': rec.max_hotel_stars and rec.max_hotel_stars or 5
                    })
                rules.update({
                    rec.provider_type_id.code: temp_dict
                })
        return rules


class TtCustomerJobRules(models.Model):
    _name = 'tt.customer.job.rules'
    _description = 'Tour & Travel - Customer Job Rules'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('Name', compute='_compute_name')
    job_position_id = fields.Many2one('tt.customer.job.position', 'Job Position')

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_access_type = fields.Selection(ACCESS_TYPE, 'Provider Access Type', default='all')
    provider_ids = fields.Many2many('tt.provider', "tt_provider_tt_job_rules_rel", "tt_job_rules_id",
                                                "tt_provider_id", "Provider", domain='[("provider_type_id", "=", provider_type_id)]')
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True,
                                           help='Only for Airline products.')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_customer_job_position_carrier_rel', 'job_position_id',
                                   'carrier_id', string='Carriers', domain='[("provider_type_id", "=", provider_type_id)]', help='Only for Airline products.')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    max_price = fields.Monetary('Max Price', default=0, help='Put 0 for unlimited max price.')
    max_hotel_stars = fields.Selection([(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], 'Max Hotel Stars', default=5,
                                       help='Only for Hotel products.')
    max_cabin_class = fields.Selection([('economy', 'Economy'), ('premium', 'Premium Economy'),
                                        ('business', 'Business Class'), ('first', 'First Class / Executive')],
                                       'Max Cabin Class', default='first', help='Only for Airline and Train products.')

    @api.onchange('provider_type_id', 'provider_access_type', 'provider_ids', 'carrier_access_type', 'carrier_ids')
    @api.depends('provider_type_id', 'provider_access_type', 'provider_ids', 'carrier_access_type', 'carrier_ids')
    def _compute_name(self):
        for rec in self:
            final_name = rec.provider_type_id and rec.provider_type_id.name or ''
            prov_name_list = [rec2.name for rec2 in rec.provider_ids]
            carrier_name_list = [rec2.name for rec2 in rec.carrier_ids]
            # if rec.provider_access_type == 'allow':
            #     final_name += ' (Allow In Provider [%s])' % ', '.join(prov_name_list)
            # elif rec.provider_access_type == 'restrict':
            #     final_name += ' (Restrict In Provider [%s])' % ', '.join(prov_name_list)
            # else:
            #     final_name += ' (In All Providers)'
            if rec.carrier_access_type == 'allow':
                final_name += ' (Allow In Carrier [%s])' % ', '.join(carrier_name_list)
            elif rec.carrier_access_type == 'restrict':
                final_name += ' (Restrict In Carrier [%s])' % ', '.join(carrier_name_list)
            else:
                final_name += ' (In All Carriers)'
            rec.name = final_name

    def get_provider_code_list(self):
        res = []
        for rec in self.provider_ids:
            res.append(rec.code)
        return res

    def get_carrier_code_list(self):
        res = []
        for rec in self.carrier_ids:
            res.append(rec.code)
        return res
