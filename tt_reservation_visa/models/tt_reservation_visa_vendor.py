from odoo import api, fields, models, _


class VisaVendor(models.Model):
    _name = 'tt.reservation.visa.vendor'
    _description = 'Reservation Visa Vendor'

    name = fields.Char('Name')
    description = fields.Text('Description')


class VisaVendorLines(models.Model):
    _name = 'tt.reservation.visa.vendor.lines'
    _description = 'Reservation Visa Vendor Lines'

    provider_id = fields.Many2one('tt.provider.visa', 'Provider')
    visa_id = fields.Many2one('tt.reservation.visa', 'Visa ID')
    vendor_id = fields.Many2one('tt.reservation.visa.vendor', 'Vendor')
    reference_number = fields.Char('Reference Number')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Selling')
    nta_amount = fields.Monetary('NTA Amount')
    passenger_ids = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger',
                                    domain=lambda self: self.domain_passenger())  # "[('visa_id.provider_booking_ids', 'in', provider_id)]"
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
    is_upsell_ledger_created = fields.Boolean('Is Upsell Ledger Created')
    is_invoice_created = fields.Boolean('Is Invoice Created')

    def domain_passenger(self):
        return [('visa_id', '=', self.visa_id)]

    def to_dict(self):
        res = {
            'order_number': self.provider_id.pnr,
            'vendor': self.vendor_id.name,
            'reference_number': self.reference_number,
            'currency': self.currency_id.name,
            'amount': self.amount,
            'payment_date': self.payment_date
        }
        return res

    def pax_to_dict(self):
        psg_list = []
        for psg in self.passenger_ids:
            psg_list.append({
                'name': psg.name
            })
        return psg_list
