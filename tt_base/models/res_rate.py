from odoo import models, fields, api
from ...tools.api import Response
import traceback,logging

_logger = logging.getLogger(__name__)

class ResRate(models.Model):
    _name = 'tt.provider.rate'
    _rec_name = 'currency_id'
    _description = 'Tour & Travel - Rate'
    _order = 'date DESC'

    name = fields.Char()
    provider_id = fields.Many2one('tt.provider', 'Provider')
    date = fields.Date(string="Date", required=False)
    currency_id = fields.Many2one('res.currency', 'Currency')
    rate_currency_id = fields.Many2one('res.currency', 'Rate Currency', default=lambda self: self.env.ref('base.IDR'))
    buy_rate = fields.Monetary('Buy Rate', currency_field='rate_currency_id')
    sell_rate = fields.Monetary('Sell Rate', currency_field='rate_currency_id')
    active = fields.Boolean('Active', default=True)


    def get_currency_rate_api(self):
        try:
            _objs = self.search([])
            # response = [rec.get_ssr_data() for rec in _objs]
            currency_rate = [rec.get_currency_rate_data() for rec in _objs]
            response = {
                'currency_rate_data': currency_rate,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get SSR API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_currency_rate_data(self):
        res = {
            'name': self.name,
            'provider': self.provider_id.code,
            'date': self.date.strftime('%Y-%m-%d'),
            'base_currency': self.currency_id.name,
            'to_currency':  self.rate_currency_id.name,
            'buy_rate': self.buy_rate,
            'sell_rate': self.sell_rate,
            'active': self.active,
        }
        return res
