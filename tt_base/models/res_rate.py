from odoo import models, fields, api
from ...tools.api import Response
import traceback,logging

_logger = logging.getLogger(__name__)

class ResRate(models.Model):
    _name = 'tt.provider.rate'
    _rec_name = 'currency_id'
    _description = 'Tour & Travel - Vendor Rate'
    _order = 'date DESC'

    name = fields.Char()
    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider HO Data')
    date = fields.Date(string="Date", required=False)
    currency_id = fields.Many2one('res.currency', 'Currency')
    rate_currency_id = fields.Many2one('res.currency', 'Rate Currency', default=lambda self: self.env.ref('base.IDR'))
    buy_rate = fields.Monetary('Buy Rate', currency_field='rate_currency_id')
    sell_rate = fields.Monetary('Sell Rate', currency_field='rate_currency_id')
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    active = fields.Boolean('Active', default=True)


    def get_currency_rate_api(self):
        try:
            _objs = self.search([])
            # response = [rec.get_ssr_data() for rec in _objs]
            currency_rate = {}
            for rec in _objs:
                if rec.provider_ho_data_id:
                    if rec.provider_ho_data_id.ho_id.seq_id not in currency_rate:
                        currency_rate[rec.provider_ho_data_id.ho_id.seq_id] = {}
                    if rec.provider_ho_data_id.provider_id.code not in currency_rate[rec.provider_ho_data_id.ho_id.seq_id]:
                        currency_rate[rec.provider_ho_data_id.ho_id.seq_id][rec.provider_ho_data_id.provider_id.code] = []
                    currency_rate[rec.provider_ho_data_id.ho_id.seq_id][rec.provider_ho_data_id.provider_id.code].append(rec.get_currency_rate_data())

            response = {
                'currency_rate_data': currency_rate,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Currency Rate API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_currency_rate_data(self):
        res = {
            'name': self.name,
            'provider': self.provider_ho_data_id.provider_id.code,
            'date': self.date.strftime('%Y-%m-%d'),
            'base_currency': self.currency_id.name,
            'to_currency':  self.rate_currency_id.name,
            'buy_rate': self.buy_rate,
            'sell_rate': self.sell_rate,
            'active': self.active,
        }
        return res


class AgentResRate(models.Model):
    _name = 'tt.agent.rate'
    _rec_name = 'base_currency_id'
    _description = 'Tour & Travel - Agent Rate'

    name = fields.Char(readonly=True, compute="_compute_name")
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent') ## NANTI DIHAPUS PINDAH KE HO_ID
    base_currency_id = fields.Many2one('res.currency', 'Base Currency')
    to_currency_id = fields.Many2one('res.currency', 'To Currency', default=lambda self: self.env.ref('base.IDR'))
    rate = fields.Monetary('Rate', currency_field='to_currency_id')
    is_show = fields.Boolean('Show', default=True)
    active = fields.Boolean('Active', default=True)

    @api.onchange('ho_id')
    @api.depends('base_currency_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s - %s" % (rec.ho_id.name, rec.base_currency_id.name)

    def get_agent_currency_rate_api(self, context):
        try:
            # _objs = self.search([('active','=',True)]) ## untuk all agent o3
            _objs = self.search([('active', '=', True), ('ho_id.seq_id', '=', context['co_ho_seq_id']), ('is_show','=', True), ('active', '=', True)])  ## untuk ambil agent HO
            # response = [rec.get_ssr_data() for rec in _objs]
            response = {
                "agent": {},
                "currency_list": []
            }
            for obj in _objs:
                if not response['agent'].get(obj.ho_id.seq_id):
                    response['agent'][obj.ho_id.seq_id] = {}
                if obj.base_currency_id.code not in response['currency_list']:
                    response['currency_list'].append(obj.to_currency_id.name)
                response['agent'][obj.ho_id.seq_id][obj.to_currency_id.name] = obj.get_currency_rate_data()
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Agent Rate API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_currency_rate_data(self):
        res = {
            'name': self.name,
            'base_currency': self.base_currency_id.name,
            'to_currency':  self.to_currency_id.name,
            'rate': self.rate,
        }
        return res
