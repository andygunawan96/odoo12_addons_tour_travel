from odoo import api, fields, models
from ...tools import variables
from datetime import datetime


class ProviderVisaPassengers(models.Model):
    _name = 'tt.provider.visa.passengers'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.visa', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    pricelist_id = fields.Many2one('tt.reservation.visa.pricelist', 'Visa Pricelist')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
        }
        return res


class TtProviderVisa(models.Model):
    _name = 'tt.provider.visa'
    _rec_name = 'pnr'
    _description = 'Rodex Model'

    pnr = fields.Char('PNR')  # di isi aja order number
    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.visa', 'Order Number', ondelete='cascade')
    visa_id = fields.Many2one('tt.reservation.visa.pricelist', 'Visa Pricelist')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_visa_booking_id', 'Cost Service Charges')

    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    departure_date = fields.Char('Journey Date', readonly=True,
                                 states={'draft': [('readonly', False)]})

    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)

    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    expired_date = fields.Datetime('Expired Date', readonly=True)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    vendor_ids = fields.One2many('tt.reservation.visa.vendor.lines', 'provider_id', 'Expenses')

    passenger_ids = fields.One2many('tt.provider.visa.passengers', 'provider_id', 'Passengers')

    def action_booked_api_visa(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
                # 'hold_date': datetime.strptime(provider_data['hold_date'],"%Y-%m-%d %H:%M:%S"),
            })

    def action_issued_api_visa(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
            })

    def action_expired(self):
        self.state = 'cancel2'

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['pax_count'] = 0  # jumlah pax
            scs['total'] = 0  # total pricing
            scs['currency_id'] = currency_obj.get_id('IDR')  # currency (IDR)
            scs['foreign_currency_id'] = currency_obj.get_id('IDR')  # currency (foreign)
            scs['provider_visa_booking_id'] = self.id  # id provider visa
            for psg in self.passenger_ids:
                if scs['pax_type'] == psg.pax_type:
                    scs['passenger_visa_ids'].append(psg.id)  # add passenger to passenger visa ids
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
            scs['passenger_visa_ids'] = [(6, 0, scs['passenger_visa_ids'])]
            scs['description'] = self.pnr and self.pnr or ''
            if scs['total'] != 0:
                service_chg_obj.create(scs)

    def delete_service_charge(self):
        for rec in self.cost_service_charge_ids:
            rec.unlink()

    def action_create_ledger(self):
        if not self.is_ledger_created:
            self.write({'is_ledger_created': True})
            self.env['tt.ledger'].action_create_ledger(self, self.env.user.id)

    def to_dict(self):
        passenger_list = []
        for rec in self.passenger_ids:
            passenger_list.append(rec.to_dict())
        vendor_list = []
        for rec in self.vendor_ids:
            vendor_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'country': self.country_id.name,
            'country_code': self.country_id.code,
            'country_id': self.country_id,
            'departure_date': self.departure_date,
            'passengers': passenger_list,
            'vendors': vendor_list
        }
        return res
