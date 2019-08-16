from odoo import api, fields, models, _


class PassportVendor(models.Model):
    _name = 'tt.reservation.passport.vendor'
    _description = 'Rodex Model'

    name = fields.Char('Name')
    description = fields.Text('Description')


class PassportVendorLines(models.Model):
    _name = 'tt.reservation.passport.vendor.lines'
    _description = 'Rodex Model'

    passport_id = fields.Many2one('tt.reservation.passport', 'passport ID')
    vendor_id = fields.Many2one('tt.reservation.passport.vendor', 'Vendor')
    reference_number = fields.Char('Reference Number')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount')
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
