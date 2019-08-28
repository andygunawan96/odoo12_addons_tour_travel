from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class PricingAgent(models.Model):
    _name = 'tt.pricing.agent'
    _description = 'Rodex Model'

    name = fields.Char('Name', readonly=1)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_pricing_agent_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers')
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_amount = fields.Monetary('Fee Amount', default=False)
    is_per_route = fields.Boolean('Is per Route', default=False)
    is_per_segment = fields.Boolean('Is per Segment', default=False)
    is_per_pax = fields.Boolean('is per Pax', default=0)
    loop_level = fields.Integer('Loop Level', default=0)
    line_ids = fields.One2many('tt.pricing.agent.line', 'pricing_id', 'Pricing')
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s - %s' % (self.agent_type_id.code.title(), self.provider_type_id.code.title())
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgent, self).create(values)
        res.write({})
        return res

    def write(self, values):
        res = super(PricingAgent, self).write(values)
        if not values.get('name'):
            self.write({'name': self.get_name()})
        return res

    def get_pricing_agent_api(self, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            if not provider_obj:
                raise Exception('Provider Type not found')
            _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', 1)])
            response = {}
            for rec in _obj:
                response.update({
                    rec.agent_type_id.code: rec.get_data()
                })
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_data(self):
        line_dict = {}
        line_ids = []
        [line_dict.update({rec.agent_type_id.code: rec.get_data()}) for rec in self.line_ids if rec.active]
        provider_ids = [rec.code for rec in self.provider_ids]
        res = {
            'agent_type_id': self.agent_type_id.get_data(),
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'provider_ids': provider_ids,
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
            'currency': self.currency_id and self.currency_id.name,
            'fee_amount': self.fee_amount,
            'is_per_route': self.is_per_route,
            'is_per_segment': self.is_per_segment,
            'is_per_pax': self.is_per_pax,
            'loop_level': self.loop_level,
            # 'line_ids': line_ids,
            'line_dict': line_dict,
        }
        return res

    def get_agent_hierarchy(self, agent_id, hierarchy=[]):
        hierarchy.append({
            'agent_id': agent_id.id,
            'agent_name': agent_id.name,
            'agent_type_id': agent_id.agent_type_id.id,
            'code': agent_id.agent_type_id.code,
        })
        if agent_id.parent_agent_id:
            return self.get_agent_hierarchy(agent_id.parent_agent_id, hierarchy)
        else:
            return hierarchy

    def get_commission(self, amount, agent_id, provider_type_id, provider_ids=[]):
        price_obj = self.search([('agent_type_id', '=', agent_id.agent_type_id.id),
                 ('provider_type_id', '=', provider_type_id.id)], limit=1)
        print(price_obj.read())
        vals_list = []
        remaining_diff = 0

        if price_obj.basic_amount_type == 'percentage':
            perc_remaining = 100
            comm = amount * price_obj.basic_amount / 100
            rac_count = 0
            diff_count = 0

            vals = {
                'agent_id': agent_id.id,
                'agent_name': agent_id.name,
                'agent_type_id': agent_id.agent_type_id.id,
                'amount': comm,
                'type': 'RAC',
                'code': 'rac'
            }
            vals_list.append(vals)
            rac_count += 1

            perc_remaining -= price_obj.basic_amount
            remaining_diff = amount - comm

            # find hierarchy agent
            agent_hierarchy = self.get_agent_hierarchy(agent_id, hierarchy=[])
            print(agent_hierarchy)
            curr_rule = {}

            for line in self.line_ids:
                if line.basic_amount_type == 'percentage':
                    curr_rule[line.agent_type_id.code] = amount * line.basic_amount / 100

                    perc_remaining -= line.basic_amount
                    remaining_diff -= curr_rule[line.agent_type_id.code]
            if self.loop_level:
                curr_rule[self.agent_type_id.code] = (amount * perc_remaining / 100) / self.loop_level

            agent_type_count = {}
            agent_type_src = ''
            for idx, rec in enumerate(agent_hierarchy):
                if idx == 0:
                    agent_type_src = rec['code']  # src = yang pesan
                    continue

                vals = {}
                agent_type_rec = rec['code']
                if not agent_type_count.get(agent_type_rec):  # jika agent_type_rec empty
                    agent_type_count[agent_type_rec] = 0
                agent_type_count[agent_type_rec] += 1

                # agent type harus sama, dan count harus lebih kecil dr loop level
                if agent_type_count[agent_type_rec] <= self.loop_level and agent_type_rec == agent_type_src:
                    amount = curr_rule[agent_type_rec]  # amount = 1
                    remaining_diff -= amount  # remaining_diff = 2 - 1 = 1
                elif curr_rule.get(agent_type_rec) and agent_type_count[agent_type_rec] == 1:
                    amount = curr_rule[agent_type_rec]  # amount pasti 1
                else:
                    amount = 0
                vals.update({
                    'agent_id': rec['agent_id'],
                    'agent_name': rec['agent_name'],
                    'agent_type_id': rec['agent_type_id'],
                    'type': 'RAC',
                    'code': 'rac' + str(rac_count),
                    'amount': amount,
                })
                vals_list.append(vals)
                rac_count += 1
            ho_agent_type_id = self.env['tt.agent.type'].search([('code', '=', 'ho')], limit=1).id
            ho_agent = self.env['tt.agent'].search([('agent_type_id', '=', ho_agent_type_id)], limit=1)
            vals_list.append({
                'agent_id': ho_agent.id,
                'agent_type_id': ho_agent_type_id,
                'agent_name': ho_agent.name,
                'type': 'remaining_diff',
                'code': 'diff',
                'amount': remaining_diff,
            })

            # for line in self.line_ids:
            #     if line.agent_type_id.code == 'citra':
            #         vals = {
            #             'agent_type_id': line.agent_type_id.id,
            #             'amount': amount * line.basic_amount / 100,
            #             'type': 'RAC',
            #             'code': 'rac' + str(n)
            #         }
            #         vals_list.append(vals)
            #         perc_remaining -= line.basic_amount
            #         n += 1
            #     elif line.agent_type_id.code == 'ho':
            #         vals = {
            #             'agent_type_id': line.agent_type_id.id,
            #             'amount': amount * line.basic_amount / 100,
            #             'type': 'RAC',
            #             'code': 'rac' + str(n)
            #         }
            #         vals_list.append(vals)
            #         perc_remaining -= line.basic_amount
            # if perc_remaining > 0:
            #     if self.loop_level > 0:
            #         for level in range(self.loop_level):
            #             pass
            #     else:
            #         vals = {
            #             'agent_type_id': self.env['tt.agent.type'].search([('code', '=', 'ho')], limit=1).id,
            #             'amount': amount * perc_remaining / 100,
            #             'type': 'RAC',
            #             'code': 'diff'
            #         }
            #         vals_list.append(vals)
        elif self.basic_amount_type == 'amount':
            vals = {
                'agent_type_id': self.agent_type_id.id,
                'amount': self.basic_amount,
                'type': 'RAC',
                'code': 'rac'
            }
            vals_list.append(vals)

            n = 1

            for line in self.line_ids:
                if line.agent_type_id.code == 'citra':
                    vals = {
                        'agent_type_id': line.agent_type_id.id,
                        'amount': line.basic_amount,
                        'type': 'RAC',
                        'code': 'rac' + str(n)
                    }
                    vals_list.append(vals)
                    n += 1

            for line in self.line_ids:
                if line.agent_type_id.code == 'ho':
                    vals = {
                        'agent_type_id': line.agent_type_id.id,
                        'amount': line.basic_amount,
                        'type': 'RAC',
                        'code': 'rac' + str(n)
                    }
                    vals_list.append(vals)

        print(vals_list)
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
    _description = 'Rodex Model'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    pricing_id = fields.Many2one('tt.pricing.agent', 'Pricing', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    active = fields.Boolean('Active', default=True)

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
        }
        return res
