from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class PricingAgent(models.Model):
    _name = 'tt.pricing.agent'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Orbis Pricing Agent Model'

    name = fields.Char('Name', compute='_compute_name_pricing', store=True)
    name_desc = fields.Char('Name Description')
    sequence = fields.Integer('Sequence', default=50, required=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_pricing_agent_provider_rel', 'pricing_id', 'provider_id', string='Providers')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_pricing_agent_carrier_rel', 'pricing_id', 'carrier_id', string='Carriers')
    provider_access_type = fields.Selection(variables.ACCESS_TYPE, 'Provider Access Type', required=True, default='all')
    display_providers = fields.Char('Display Providers', compute='_compute_display_providers', store=True, readonly=1)
    carrier_access_type = fields.Selection(variables.ACCESS_TYPE, 'Carrier Access Type', required=True, default='all')
    display_carriers = fields.Char('Display Carriers', compute='_compute_display_carriers', store=True, readonly=1)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_charge_type = fields.Selection(variables.FEE_CHARGE_TYPE, 'Fee Charge Type', default='ho')
    fee_amount = fields.Monetary('Fee Amount', default=False)
    is_per_route = fields.Boolean('Is per Route', default=False)
    is_per_segment = fields.Boolean('Is per Segment', default=False)
    is_per_pax = fields.Boolean('is per Pax', default=0)
    loop_level = fields.Integer('Loop Level', default=0)
    is_compute_infant_fee = fields.Boolean('Compute Inf Fee Amount', default=False)
    line_ids = fields.One2many('tt.pricing.agent.line', 'pricing_id', 'Pricing')
    active = fields.Boolean('Active', default=True)
    commission_charge_type = fields.Selection(variables.COMMISSION_CHARGE_TYPE, 'Commission Charge Type', default='pricing')

    origin_type = fields.Selection(variables.ACCESS_TYPE, 'Origin Type', required=True, default='all')
    origin_ids = fields.Many2many('tt.destinations', 'tt_pricing_agent_origin_rel', 'pricing_id', 'origin_id', string='Origins')
    display_origins = fields.Char('Display Origins', compute='_compute_display_origins', store=True, readonly=1)
    origin_city_ids = fields.Many2many('res.city', 'tt_pricing_agent_origin_city_rel', 'pricing_id', 'city_id', string='Origin Cities')
    display_origin_cities = fields.Char('Display Origin Cities', compute='_compute_display_origin_cities', store=True, readonly=1)
    origin_country_ids = fields.Many2many('res.country', 'tt_pricing_agent_origin_country_rel', 'pricing_id', 'country_id', string='Origin Countries')
    display_origin_countries = fields.Char('Display Origin Countries', compute='_compute_display_origin_countries', store=True, readonly=1)
    destination_type = fields.Selection(variables.ACCESS_TYPE, 'Destination Type', required=True, default='all')
    destination_ids = fields.Many2many('tt.destinations', 'tt_pricing_agent_destination_rel', 'pricing_id', 'destination_id', string='Destinations')
    display_destinations = fields.Char('Display Destinations', compute='_compute_display_destinations', store=True, readonly=1)
    destination_city_ids = fields.Many2many('res.city', 'tt_pricing_agent_destination_city_rel', 'pricing_id', 'city_id', string='Destination Cities')
    display_destination_cities = fields.Char('Display Destination Cities', compute='_compute_display_destination_cities', store=True, readonly=1)
    destination_country_ids = fields.Many2many('res.country', 'tt_pricing_agent_destination_country_rel', 'pricing_id', 'country_id', string='Destination Countries')
    display_destination_countries = fields.Char('Display Destination Countries', compute='_compute_display_destination_countries', store=True, readonly=1)
    class_of_service_type = fields.Selection(variables.ACCESS_TYPE, 'Class of Service Type', required=True, default='all')
    class_of_service_ids = fields.Many2many('tt.pricing.class.of.service', 'tt_pricing_agent_class_of_service_rel', 'pricing_id', 'class_of_service_id', string='Class of Services')
    display_class_of_services = fields.Char('Class of Services', compute='_compute_display_class_of_services', store=True, readonly=1)
    charge_code_type = fields.Selection(variables.ACCESS_TYPE, 'Charge Code Type', required=True, default='all')
    charge_code_ids = fields.Many2many('tt.pricing.charge.code', 'tt_pricing_provider_line_charge_code_rel', 'pricing_line_id', 'charge_code_id', string='Charge Codes')
    display_charge_codes = fields.Char('Charge Codes', compute='_compute_display_charge_codes', store=True, readonly=1)

    agent_ids = fields.Many2many('tt.agent', 'pricing_agent_rel', 'pricing_id', 'agent_id', string='Agents')
    agent_access_type = fields.Selection(variables.ACCESS_TYPE, 'Agent Access Type', default='all')
    display_agents = fields.Char('Display Agents', compute='_compute_display_agents', store=True, readonly=1)

    def do_compute_sequence(self):
        _objs = self.sudo().with_context(active_test=False).search([], order='sequence')
        count = 10
        line_count = 10
        for rec in _objs:
            rec.update({'sequence': count})
            count += 10
            line_objs = self.env['tt.pricing.agent.line'].sudo().with_context(active_test=False).search([('pricing_id', '=', rec.id)], order='sequence')
            for line in line_objs:
                line.update({'sequence': line_count})
                line_count += 10

    def do_compute_all_names(self):
        _objs = self.sudo().with_context(active_test=False).search([])
        for rec in _objs:
            rec._compute_display_origins()
            rec._compute_display_destinations()
            rec._compute_display_origin_cities()
            rec._compute_display_destination_cities()
            rec._compute_display_origin_countries()
            rec._compute_display_destination_countries()
            rec._compute_display_class_of_services()
            rec._compute_display_charge_codes()
            rec._compute_display_agents()
            rec._compute_name_pricing()
            rec._compute_display_providers()
            rec._compute_display_carriers()


    @api.multi
    @api.depends('origin_ids')
    def _compute_display_origins(self):
        for rec in self:
            res = [data.code for data in rec.origin_ids]
            rec.display_origins = ','.join(res)

    @api.multi
    @api.depends('destination_ids')
    def _compute_display_destinations(self):
        for rec in self:
            res = [data.code for data in rec.destination_ids]
            rec.display_destinations = ','.join(res)

    @api.multi
    @api.depends('origin_city_ids')
    def _compute_display_origin_cities(self):
        for rec in self:
            res = [data.code for data in rec.origin_city_ids]
            rec.display_origin_cities = ','.join(res)

    @api.multi
    @api.depends('destination_city_ids')
    def _compute_display_destination_cities(self):
        for rec in self:
            res = [data.code for data in rec.destination_city_ids]
            rec.display_destination_cities = ','.join(res)

    @api.multi
    @api.depends('origin_country_ids')
    def _compute_display_origin_countries(self):
        for rec in self:
            res = [data.code for data in rec.origin_country_ids]
            rec.display_origin_countries = ','.join(res)

    @api.multi
    @api.depends('destination_country_ids')
    def _compute_display_destination_countries(self):
        for rec in self:
            res = [data.code for data in rec.destination_country_ids]
            rec.display_destination_countries = ','.join(res)

    @api.multi
    @api.depends('class_of_service_ids')
    def _compute_display_class_of_services(self):
        for rec in self:
            res = [data.code for data in rec.class_of_service_ids]
            rec.display_class_of_services = ','.join(res)

    @api.multi
    @api.depends('charge_code_ids')
    def _compute_display_charge_codes(self):
        for rec in self:
            res = [data.code for data in rec.charge_code_ids]
            rec.display_charge_codes = ','.join(res)

    @api.multi
    @api.depends('agent_ids')
    def _compute_display_agents(self):
        for rec in self:
            res = [data.name for data in rec.agent_ids]
            rec.display_agents = ','.join(res)

    @api.multi
    @api.depends('agent_type_id.code','provider_type_id.code', 'agent_access_type', 'agent_ids')
    def _compute_name_pricing(self):
        for rec in self:
            rec.name = rec.get_name()

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        name_list = []
        if self.agent_type_id:
            name_list.append(self.agent_type_id.code.title())

        if self.provider_type_id:
            name_list.append(self.provider_type_id.code.title())

        if self.agent_access_type:
            name_list.append(self.agent_access_type.title())
            if self.agent_access_type != 'all':
                for rec in self.agent_ids:
                    name_list.append(str(rec.id))
        res = ' - '.join(name_list)
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

    @api.model
    def create(self, values):
        res = super(PricingAgent, self).create(values)
        res.write({})
        return res

    def write(self, values):
        res = super(PricingAgent, self).write(values)
        # 16feb2021, comment karena membuat error singleton. seharusnya yang di compute_name_pricing sudah ckup
        # if not values.get('name'):
        #     self.write({'name': self.get_name()})
        return res

    def get_pricing_agent_api(self, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            if not provider_obj:
                raise Exception('Provider Type not found')
            _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', 1)])

            qs = [rec.get_data() for rec in _obj if rec.active]

            # response = {}
            # for rec in _obj:
            #     response.update({
            #         rec.agent_type_id.code: rec.get_data()
            #     })

            response = {
                'pricing_agents': qs,
                'pricing_type': _provider_type
            }

            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_data(self):
        line_dict = {}
        line_ids = []
        [line_dict.update({rec.agent_type_id.code: rec.get_data()}) for rec in self.line_ids if rec.active]
        carrier_codes = [rec.code for rec in self.carrier_ids]
        providers = [rec.code for rec in self.provider_ids]
        agents = [rec.id for rec in self.agent_ids]
        origin_codes = [rec.code for rec in self.origin_ids]
        origin_city_ids = [rec.id for rec in self.origin_city_ids]
        origin_country_codes = [rec.code for rec in self.origin_country_ids]
        destination_codes = [rec.code for rec in self.destination_ids]
        destination_city_ids = [rec.id for rec in self.destination_city_ids]
        destination_country_codes = [rec.code for rec in self.destination_country_ids]
        charge_codes = [rec.code for rec in self.charge_code_ids]
        class_of_services = [rec.code for rec in self.class_of_service_ids]
        res = {
            'id': self.id,
            'agent_type_id': self.agent_type_id.get_data(),
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'carrier_access_type': self.carrier_access_type,
            'carrier_codes': carrier_codes,
            'provider_access_type': self.provider_access_type,
            'commission_charge_type': self.commission_charge_type,
            'providers': providers,
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
            'currency': self.currency_id and self.currency_id.name,
            'fee_charge_type': self.fee_charge_type,
            'fee_amount': self.fee_amount,
            'is_per_route': self.is_per_route,
            'is_per_segment': self.is_per_segment,
            'is_per_pax': self.is_per_pax,
            'loop_level': self.loop_level,
            'is_compute_infant_fee': self.is_compute_infant_fee,
            # 'line_ids': line_ids,
            'line_dict': line_dict,
            'origin_type': self.origin_type,
            'origin_codes': origin_codes,
            'origin_city_ids': origin_city_ids,
            'origin_country_codes': origin_country_codes,
            'destination_type': self.destination_type,
            'destination_codes': destination_codes,
            'destination_city_ids': destination_city_ids,
            'destination_country_codes': destination_country_codes,
            'charge_code_type': self.charge_code_type,
            'agent_access_type': self.agent_access_type,
            'charge_codes': charge_codes,
            'agents': agents,
            'class_of_service_type': self.class_of_service_type,
            'class_of_services': class_of_services,
        }
        return res

    def get_agent_hierarchy(self, agent_id, hierarchy=[]):
        hierarchy.append({
            'commission_agent_id': agent_id.id,
            'agent_id': agent_id.id,
            'agent_name': agent_id.name,
            'agent_type_id': agent_id.agent_type_id.id,
            'code': agent_id.agent_type_id.code,
        })
        if agent_id.sudo().parent_agent_id and agent_id.sudo().parent_agent_id.name != agent_id.sudo().name:
            return self.get_agent_hierarchy(agent_id.sudo().parent_agent_id, hierarchy)
        else:
            return hierarchy

    def get_commission(self, input_commission, agent_id, provider_type_id, provider_ids=[]):
        """ Fungsi untuk membagi commisison berdasarkan jenis provider type dan agent type """

        """ Search object pricing agent berdasarkan provider type dan agent type """
        price_obj = self.sudo().search([('agent_type_id', '=', agent_id.agent_type_id.id),
                                 ('provider_type_id', '=', provider_type_id.id)], limit=1)
        vals_list = []  # output list of pricing
        remaining_diff = 0  # sisa diff yang jika masih ada sisa, akan dimasukkan ke HO
        perc_remaining = 100
        agent_comm = 0
        rac_count = 0

        """ get basic amount untuk agent yang pesan """
        if input_commission > 0:
            if price_obj.basic_amount_type == 'percentage':
                """ Jika basic amount type = percentage """
                agent_comm = input_commission * price_obj.basic_amount / 100  # jika percentage, kalikan dg basic amount / 100
                perc_remaining -= price_obj.basic_amount  # sisa percentage dikurangi dg basic amount
                remaining_diff = input_commission - agent_comm  # sisa diff = input komisi awal - komisi agent yang pesan
            elif price_obj.basic_amount_type == 'amount':
                """ Jika basic amount type = amount """
                agent_comm = price_obj.basic_amount  # jika amount, langsung isi basic amount
                remaining_diff = input_commission - agent_comm  # sisa diff = input komisi awal - komisi agent yang pesan

            """ Set pricing untuk agent yang pesan """
            vals = {
                'commission_agent_id': agent_id.id,
                'agent_id': agent_id.id,
                'agent_name': agent_id.name,
                'agent_type_id': agent_id.agent_type_id.id,
                'amount': agent_comm,
                'type': 'RAC',
                'code': 'rac'
            }
            vals_list.append(vals)
            rac_count += 1

            """ list agents hierarchy (list of dict mulai dari agent yang pesan hingga HO) """
            agent_hierarchy = self.sudo().get_agent_hierarchy(agent_id, hierarchy=[])

            curr_rule = {}

            """ Looping uplines untuk menentukan pricing rule & nominal nya """
            for line in price_obj.line_ids:
                """ jika amount type dari upline = percentage """
                if line.basic_amount_type == 'percentage':
                    curr_rule[line.agent_type_id.code] = input_commission * line.basic_amount / 100  # set amount agent type

                    perc_remaining -= line.basic_amount  # kurangi perc_remaining dg basic amount dari line
                    # remaining_diff -= curr_rule[line.agent_type_id.code]  # kurangi nilai diff sejumlah amount dari agent type
                    """ jika amount type dari upline = amount """
                elif line.basic_amount_type == 'amount':
                    curr_rule[line.agent_type_id.code] = line.basic_amount  # set amount agent type
            if price_obj.loop_level:
                curr_rule[price_obj.agent_type_id.code] = (input_commission * perc_remaining / 100) / price_obj.loop_level

            """ Loop line ids """
            for line in price_obj.line_ids:
                for idx, rec in enumerate(agent_hierarchy):
                    if idx == 0:  # 0 = index agent yang pesan
                        continue

                    if line.agent_type_id.id == rec['agent_type_id']:
                        amount = curr_rule[line.agent_type_id.code]
                        remaining_diff -= amount
                        vals = {
                            'commission_agent_id': rec['commission_agent_id'],
                            'agent_id': rec['agent_id'],
                            'agent_name': rec['agent_name'],
                            'agent_type_id': rec['agent_type_id'],
                            'type': 'RAC',
                            'code': 'rac' + str(rac_count),
                            'amount': amount,
                        }
                        vals_list.append(vals)
                        rac_count += 1
                        break

            """ Jika masih ada diff """
            if remaining_diff > 0:
                ho_obj = agent_id.get_ho_parent_agent()
                vals = {
                    'commission_agent_id': ho_obj and ho_obj.id or False,
                    'agent_id': ho_obj and ho_obj.id or False,
                    'agent_name': ho_obj and ho_obj.name or False,
                    'agent_type_id': ho_obj and ho_obj.agent_type_id.id or False,
                    'type': 'RAC',
                    'code': 'dif',
                    'amount': remaining_diff,
                }
                vals_list.append(vals)

            #     """ Tentukan jumlah pembagian untuk diff """
            #     div = 0
            #     for idx, rec in enumerate(agent_hierarchy):
            #         if idx == 0:  # 0 = index agent yang pesan
            #             continue
            #         if rec['agent_type_id'] == price_obj.agent_type_id.id:
            #             if div != price_obj.loop_level:
            #                 div += 1
            #         elif rec['agent_type_id'] == self.env.ref('tt_base.rodex_ho').agent_type_id.id:
            #             if div != price_obj.loop_level:
            #                 div += 1
            #
            #     """ Cek jika remaining diff > 0"""
            #     if remaining_diff > 0:
            #         loop_level = price_obj.loop_level
            #         for idx, rec in enumerate(agent_hierarchy):
            #             if idx == 0:  # 0 = index agent yang pesan
            #                 continue
            #
            #             if loop_level > 0 and rec['agent_type_id'] == price_obj.agent_type_id.id:
            #                 amount = remaining_diff / div
            #                 vals = {
            #                     'commission_agent_id': rec['commission_agent_id'],
            #                     'agent_id': rec['agent_id'],
            #                     'agent_name': rec['agent_name'],
            #                     'agent_type_id': rec['agent_type_id'],
            #                     'type': 'RAC',
            #                     'code': 'dif',
            #                     'amount': amount,
            #                 }
            #                 vals_list.append(vals)
            #             elif loop_level > 0 and rec['agent_type_id'] == self.env.ref('tt_base.rodex_ho').agent_type_id.id:
            #                 amount = remaining_diff / div
            #                 vals = {
            #                     'commission_agent_id': rec['commission_agent_id'],
            #                     'agent_id': rec['agent_id'],
            #                     'agent_name': rec['agent_name'],
            #                     'agent_type_id': rec['agent_type_id'],
            #                     'type': 'RAC',
            #                     'code': 'dif',
            #                     'amount': amount,
            #                 }
            #                 vals_list.append(vals)
            #             elif loop_level == 0 and rec['agent_type_id'] == self.env.ref('tt_base.rodex_ho').agent_type_id.id:
            #                 amount = remaining_diff
            #                 vals = {
            #                     'commission_agent_id': rec['commission_agent_id'],
            #                     'agent_id': rec['agent_id'],
            #                     'agent_name': rec['agent_name'],
            #                     'agent_type_id': rec['agent_type_id'],
            #                     'type': 'RAC',
            #                     'code': 'dif',
            #                     'amount': amount,
            #                 }
            #                 vals_list.append(vals)
            #
            # elif price_obj.basic_amount_type == 'amount':
            #     n = 1
            #
            #     for line in price_obj.line_ids:
            #         vals = {
            #             'agent_type_id': line.agent_type_id.id,
            #             'amount': line.basic_amount,
            #             'type': 'RAC',
            #             'code': 'rac' + str(n)
            #         }
            #         vals_list.append(vals)
            #         n += 1
                #     if line.agent_type_id.code == 'citra':
                #         vals = {
                #             'agent_type_id': line.agent_type_id.id,
                #             'amount': line.basic_amount,
                #             'type': 'RAC',
                #             'code': 'rac' + str(n)
                #         }
                #         vals_list.append(vals)
                #         n += 1
                #
                # for line in price_obj.line_ids:
                #     if line.agent_type_id.code == 'ho':
                #         vals = {
                #             'agent_type_id': line.agent_type_id.id,
                #             'amount': line.basic_amount,
                #             'type': 'RAC',
                #             'code': 'rac' + str(n)
                #         }
                #         vals_list.append(vals)

        return vals_list

    def split_commission(self, base_comm, provider, context):
        user_info = self.get_uplines(context)
        agent_obj = self.pricing_agent.get(context['co_agent_type_code'])
        comm = base_comm
        channel_comm = []
        remaining_diff = 0

        if agent_obj:
            # Agent Commission
            if agent_obj['basic_amount_type'] == 'percentage':
                # jika percentage, comm = total komisi * amount / 100
                comm = base_comm * agent_obj['basic_amount'] / 100
            else:
                # jika amount, comm = amount
                comm = agent_obj['basic_amount']
            remaining_diff = base_comm - comm

            # Upline
            curr_rule = {}
            for line_id in agent_obj['line_dict']:
                line_obj = agent_obj['line_dict'][line_id]
                if line_obj['basic_amount_type'] == 'percentage':
                    curr_rule[line_id] = base_comm * line_obj['basic_amount'] / 100
                else:
                    curr_rule[line_id] = line_obj['basic_amount']
                remaining_diff -= curr_rule[line_id]
            if agent_obj['loop_level']:
                curr_rule[agent_obj['agent_type_id']['code']] = remaining_diff / agent_obj['loop_level']

            agent_type_count = {}
            agent_type_src = ''
            for idx, rec in enumerate(user_info):
                if idx == 0:
                    agent_type_src = rec['agent_type_id']['code']  # src = yang pesan
                    continue

                agent_type_rec = rec['agent_type_id']['code']
                if not agent_type_count.get(agent_type_rec):  # jika agent_type_rec empty
                    agent_type_count[agent_type_rec] = 0
                agent_type_count[agent_type_rec] += 1

                # agent type harus sama, dan count harus lebih kecil dr loop level
                if agent_type_count[agent_type_rec] <= agent_obj['loop_level'] and agent_type_rec == agent_type_src:
                    amount = curr_rule[agent_type_rec]  # amount = 1
                    remaining_diff -= amount  # remaining_diff = 2 - 1 = 1
                elif curr_rule.get(agent_type_rec) and agent_type_count[agent_type_rec] == 1:
                    amount = curr_rule[agent_type_rec]  # amount pasti 1
                else:
                    amount = 0
                channel_comm.append({
                    'agent_id': rec['id'],
                    'agent_name': rec['name'],
                    'type': 'channel_commission',
                    'amount': amount,
                })
            channel_comm.append({
                'agent_id': '',
                'agent_name': '',
                'type': 'remaining_diff',
                'amount': remaining_diff,
            })
        return comm, channel_comm


class PricingAgentLine(models.Model):
    _name = 'tt.pricing.agent.line'
    _inherit = 'tt.history'
    _description = 'Pricing Agent Line'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    pricing_id = fields.Many2one('tt.pricing.agent', 'Pricing', readonly=True, ondelete='cascade')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    active = fields.Boolean('Active', default=True)
    commission_charge_type = fields.Selection(variables.COMMISSION_CHARGE_TYPE, 'Commission Charge Type', default='pricing')

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s - Level %s' % (self.pricing_id.name, self.level)
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgentLine, self).create(values)
        return res

    def write(self, values):
        return super(PricingAgentLine, self).write(values)

    def get_data(self):
        res = {
            'sequence': self.sequence,
            'agent_type_id': self.agent_type_id.get_data(),
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
            'commission_charge_type': self.commission_charge_type,
        }
        return res
