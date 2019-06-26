from odoo import api, fields, models, _


class VisaVendor(models.Model):
    _name = 'tt.visa.vendor'

    name = fields.Char('Name')
    description = fields.Text('Description')


class VisaVendorLines(models.Model):
    _name = 'tt.visa.vendor.lines'

    visa_id = fields.Many2one('tt.visa', 'Visa ID')
    vendor_id = fields.Many2one('tt.visa.vendor', 'Vendor')
    reference_number = fields.Char('Reference Number')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount')
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
