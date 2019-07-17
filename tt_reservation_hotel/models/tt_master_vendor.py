from odoo import models, fields, api


class HotelCitySearch(models.Model):
    _name = 'tt.provider.search'

    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    # vendor_id = fields.Many2one('tt.master.vendor', 'Vendor')
    country_id = fields.Many2one('res.country', 'Country', required=True)
    is_all_city = fields.Boolean('Apply to all City', default=True)
    is_apply = fields.Boolean('Apply Search', default=True)
    line_ids = fields.One2many('tt.provider.search.line', 'vendor_search_id', 'Line(s)')

    # def compute(self):
    #     if self.country_id:
    #         self.city_ids = [(6, 0, tags)]
        # else:
        #     raise UserError(_('Please enter Country first.'))


class HotelCitySearchLine(models.Model):
    _name = 'tt.provider.search.line'

    vendor_search_id = fields.Many2one('tt.provider.search', 'Vendor Search')
    city_id = fields.Many2one('res.city', 'City', required=True)
    is_apply = fields.Boolean('Apply Search', default=True)


class ProductPricing(models.Model):
    _name = 'tt.product.pricing'
    _order = 'sequence'

    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    vendor2_id = fields.Many2one('res.partner', 'Citra Price', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    # vendor_id = fields.Many2one('tt.master.vendor', 'Vendor')
    vendor_comm_id = fields.Many2one('res.partner', 'Vendor Commission', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    # vendor_comm_id = fields.Many2one('tt.master.vendor', 'Vendor Commission')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    sequence = fields.Integer('Sequence', default=20, help='Always Give base Price seq 99')
    min_price = fields.Monetary('Min. Price')
    max_price = fields.Monetary('Max. Price')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    amount = fields.Monetary('Amount')
    percentage = fields.Monetary('Percentage (%)')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'In Progress'),
                              ('cancel', 'Expired')], default='draft')


class VendorCurrency(models.Model):
    _name = 'tt.vendor.currency'
    _order = 'sequence'
    _rec_name = 'orig_currency_id'

    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    orig_currency_id = fields.Many2one('res.currency', 'Origin Currency')
    sequence = fields.Integer('Sequence', default=20, help='Always Give base Price seq 99')
    date = fields.Date('Date')
    sell_rate = fields.Monetary('Sell Rate')
    buy_rate = fields.Monetary('Buy Rate')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'In Progress'),
                              ('cancel', 'Expired')], default='draft')


class TtMasterVendor(models.Model):
    # _inherit = 'tt.master.vendor'
    _inherit = 'res.partner'

    line_ids = fields.One2many('tt.provider.search', 'vendor_id', 'Search in')
    price_rule_ids = fields.One2many('tt.product.pricing', 'vendor_id', 'Pricing')
    citra_price_ids = fields.One2many('tt.product.pricing', 'vendor2_id', 'Citra Price')
    vendor_currency_ids = fields.One2many('tt.vendor.currency', 'vendor_id', 'Currency')
    commission_rule_ids = fields.One2many('tt.product.pricing', 'vendor_comm_id', 'Commission')

    @api.multi
    def action_view_ledger(self):
        action = self.env.ref('tt_hotel.action_vendor_ledger').read()[0]
        action['domain'] = [('vendor_id', '=', self.id)]
        action['context'] = {
            'default_vendor_id': self.id,
        }
        return action

    def find_rate(self, date, currency_id):
        records = self.vendor_currency_ids.filtered(lambda x:x.orig_currency_id.id == currency_id and x.date < date)
        return records and records[0] or False
