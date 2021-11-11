from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
from ...tools import variables
from ...tools.api import Response
import json, logging
from ...tools import ERR
import traceback


_logger = logging.getLogger(__name__)


class TtFrequentFlyerAirline(models.Model):
    _name = 'tt.frequent.flyer.airline'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Frequent Flyer Airline'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence', default=50)
    active = fields.Boolean('Active', default=True)
    provider_access_type = fields.Selection(variables.ACCESS_TYPE, 'Provider Access Type', required=True, default='allow')
    provider_ids = fields.Many2many('tt.provider', 'frequent_flyer_airline_provider_rel', 'frequent_flyer_airline_id', 'provider_id', 'Providers')
    display_providers = fields.Char('Display Providers', compute='_compute_display_providers', store=True, readonly=1)
    carrier_access_type = fields.Selection(variables.ACCESS_TYPE, 'Carrier Access Type', required=True, default='allow')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'frequent_flyer_airline_carrier_rel', 'frequent_flyer_airline_id', 'carrier_id', 'Carriers')
    display_carriers = fields.Char('Display Carriers', compute='_compute_display_carriers', store=True, readonly=1)
    loyalty_program_ids = fields.Many2many('tt.loyalty.program', 'frequent_flyer_airline_loyalty_program_rel', 'frequent_flyer_airline_id', 'loyalty_program_id', 'Loyalty Programs')

    def to_dict(self):
        # providers = [{'name': rec.name, 'code': rec.code} for rec in self.provider_ids if rec.active]
        # carriers = [{'name': rec.name, 'code': rec.code} for rec in self.carrier_ids if rec.active]
        provider_codes = [rec.code for rec in self.provider_ids if rec.active]
        carrier_codes = [rec.code for rec in self.carrier_ids if rec.active]
        loyalty_programs = [rec.to_dict() for rec in self.loyalty_program_ids if rec.active]
        res = {
            'name': self.name,
            'provider_access_type': self.provider_access_type,
            'carrier_access_type': self.carrier_access_type,
            # 'providers': providers,
            # 'carriers': carriers,
            'provider_codes': provider_codes,
            'carrier_codes': carrier_codes,
            'loyalty_programs': loyalty_programs
        }
        return res

    @api.multi
    @api.depends('provider_ids')
    def _compute_display_providers(self):
        for rec in self:
            res = '%s' % ','.join([provider.code.title() for provider in rec.provider_ids])
            rec.display_providers = res

    @api.multi
    @api.depends('carrier_ids')
    def _compute_display_carriers(self):
        for rec in self:
            res = '%s' % ','.join([carrier.code for carrier in rec.carrier_ids])
            rec.display_carriers = res

    def get_frequent_flyer_airline_list_api(self, data, context):
        try:
            _objs = self.env['tt.frequent.flyer.airline'].sudo().search([('active', '=', 1)])
            frequent_flyer_airline_list = [rec.to_dict() for rec in _objs]
            result = {
                'frequent_flyer_airline_list': frequent_flyer_airline_list,
            }
            res = ERR.get_no_error(result)
        except:
            _logger.error('Error Get Frequent Flyer Airline List API, %s' % traceback.format_exc())
            res = ERR.get_error(500)
        return res

    # November 11, 2021 - SAM
    # New Get Frequent Flyer API
    def get_frequent_flyer_airline_api(self):
        try:
            objs = self.env['tt.frequent.flyer.airline'].sudo().search([])
            frequent_flyer_airline_data = {
                'frequent_flyer_airline_list': []
            }
            for obj in objs:
                if not obj.active:
                    continue

                vals = obj.to_dict()
                frequent_flyer_airline_data['frequent_flyer_airline_list'].append(vals)

            payload = {
                'frequent_flyer_airline_data': frequent_flyer_airline_data
            }
        except Exception as e:
            _logger.error('Error Get Frequent Flyer Airline Data, %s' % traceback.format_exc())
            payload = {}
        return payload
