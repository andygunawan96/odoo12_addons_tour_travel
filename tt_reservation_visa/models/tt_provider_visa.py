from odoo import api, fields, models
from ...tools import variables
from datetime import datetime

STATE_VISA = [
    ('fail_booked', 'Failed (Book)'),
    ('draft', 'Request'),
    ('confirm', 'Confirm to HO'),
    ('validate', 'Validated by HO'),
    ('to_vendor', 'Send to Vendor'),
    ('vendor_process', 'Proceed by Vendor'),
    ('cancel', 'Canceled'),
    ('payment', 'Payment'),
    ('in_process', 'In Process'),
    ('partial_proceed', 'Partial Proceed'),
    ('proceed', 'Proceed'),
    ('delivered', 'Delivered'),
    # ('ready', 'Sent'),
    ('done', 'Done')
]


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
    agent_id = fields.Many2one('tt.agent', 'Agent', related='booking_id.agent_id')
    visa_id = fields.Many2one('tt.reservation.visa.pricelist', 'Visa Pricelist')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    state_visa = fields.Selection(STATE_VISA, 'State', related="booking_id.state_visa")
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
    # ready_date = fields.Datetime('Ready Date', readonly=1)
    hold_date = fields.Datetime('Hold Date', readonly=1)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    vendor_ids = fields.One2many('tt.reservation.visa.vendor.lines', 'provider_id', 'Expenses')

    passenger_ids = fields.One2many('tt.provider.visa.passengers', 'provider_id', 'Passengers')

    total_price = fields.Float('Total Price', readonly=True, default=0)

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    def action_booked_api_visa(self, provider_data, api_context, hold_date):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
                'hold_date': hold_date,
            })

    def action_issued_api_visa(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
            })

    def action_fail_booked_visa(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked',
            })

    def action_expired(self):
        self.state = 'cancel2'

    def action_cancel(self):
        self.state = 'cancel'

    def action_booked(self):
        self.state = 'booked'

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['pax_count'] = 0  # jumlah pax
            scs['total'] = 0  # total pricing
            scs['passenger_visa_ids'] = []
            scs['currency_id'] = currency_obj.get_id('IDR')  # currency (IDR)
            scs['foreign_currency_id'] = currency_obj.get_id('IDR')  # currency (foreign)
            scs['provider_visa_booking_id'] = self.id  # id provider visa
            if scs['charge_code'] != 'disc':
                for psg in self.passenger_ids:
                    if scs['pax_type'] == psg.pax_type and scs['pricelist_id'] == psg.pricelist_id.id:
                        scs['passenger_visa_ids'].append(psg.passenger_id.id)  # add passenger to passenger visa ids
                        scs['pax_count'] += 1
                        scs['total'] += scs['amount']
            else:
                for psg in self.passenger_ids:
                    scs['passenger_visa_ids'].append(psg.passenger_id.id)  # add passenger to passenger visa ids
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
            scs['passenger_visa_ids'] = [(6, 0, scs['passenger_visa_ids'])]
            if 'commission_agent_id' in scs:
                scs['commission_agent_id'] = scs['commission_agent_id']
            scs['description'] = self.pnr and self.pnr or ''
            if scs['total'] != 0:
                service_chg_obj.create(scs)

    def delete_service_charge(self):
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created

    def action_create_ledger(self, issued_uid, pay_method=None):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid)

    def action_create_expenses_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        printout_expenses_id = self.env.ref('tt_report_common.action_create_expenses_invoice')
        return printout_expenses_id.report_action(self, data=datas)

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

    def get_carrier_name(self):
        return []