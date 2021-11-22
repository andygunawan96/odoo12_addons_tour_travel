from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime
import logging
import json
_logger = logging.getLogger(__name__)

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
    _description = 'Visa Passengers'

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
    _description = 'Provider Visa'

    pnr = fields.Char('PNR')  # di isi aja order number
    pnr2 = fields.Char('PNR2')
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

    ticket_ids = fields.One2many('tt.ticket.visa', 'provider_id', 'Ticket Number')

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

    def action_set_to_booked(self):
        """ Fungsi ini mengembalikan state provider ke booked & state visa ke validate """
        """ Fungsi ini dijalankan, in case terdapat salah input harga di pricelist & sudah potong ledger """

        self.action_booked()  # ubah state provider ke booked

        # ubah state visa ke validate
        self.booking_id.state = 'validate'

        # ubah state pax visa ke validate
        for psg in self.booking_id.passenger_ids:
            psg.action_validate()

        # reverse ledger
        for rec in self.booking_id.ledger_ids:
            if not rec.is_reversed:
                rec.reverse_ledger()

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    # def create_service_charge(self, service_charge_vals):
    #     service_chg_obj = self.env['tt.service.charge']
    #     currency_obj = self.env['res.currency']
    #
    #     for scs in service_charge_vals:
    #         scs['pax_count'] = 0  # jumlah pax
    #         scs['total'] = 0  # total pricing
    #         scs['passenger_visa_ids'] = []
    #         scs['currency_id'] = currency_obj.get_id('IDR')  # currency (IDR)
    #         scs['foreign_currency_id'] = currency_obj.get_id('IDR')  # currency (foreign)
    #         scs['provider_visa_booking_id'] = self.id  # id provider visa
    #         if scs['charge_code'] != 'disc':
    #             for psg in self.passenger_ids:
    #                 if scs['pax_type'] == psg.pax_type and scs['pricelist_id'] == psg.pricelist_id.id:
    #                     scs['passenger_visa_ids'].append(psg.passenger_id.id)  # add passenger to passenger visa ids
    #                     scs['pax_count'] += 1
    #                     scs['total'] += scs['amount']
    #         else:
    #             for psg in self.passenger_ids:
    #                 scs['passenger_visa_ids'].append(psg.passenger_id.id)  # add passenger to passenger visa ids
    #                 scs['pax_count'] += 1
    #                 scs['total'] += scs['amount']
    #         scs['passenger_visa_ids'] = [(6, 0, scs['passenger_visa_ids'])]
    #         if 'commission_agent_id' in scs:
    #             scs['commission_agent_id'] = scs['commission_agent_id']
    #         scs['description'] = self.pnr and self.pnr or ''
    #         if scs['total'] != 0:
    #             service_chg_obj.create(scs)

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            # update 19 Feb 2020 maximum per pax sesuai dengan pax_count dari service charge
            # scs['pax_count'] = 0
            scs_pax_count = 0
            scs['passenger_visa_ids'] = []
            scs['total'] = 0
            scs['currency_id'] = currency_obj.get_id(scs.get('currency'), default_param_idr=True)
            scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'), default_param_idr=True)
            scs['provider_visa_booking_id'] = self.id
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    scs['passenger_visa_ids'].append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    scs['total'] += scs['amount']
            scs['passenger_visa_ids'] = [(6, 0, scs['passenger_visa_ids'])]
            scs['description'] = self.pnr and self.pnr or str(self.sequence)
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

    def action_reverse_ledger_from_button(self):
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

        ##fixme salahhh, ini ke reverse semua provider bukan provider ini saja
        ## ^ harusnay sudah fix
        for rec in self.booking_id.ledger_ids:
            if rec.pnr in [self.pnr, str(self.sequence)] and not rec.is_reversed:
                rec.reverse_ledger()

        for rec in self.cost_service_charge_ids:
            rec.is_ledger_created = False

        self.write({
            'state': 'fail_refunded',
            # 'is_ledger_created': False,
            'refund_uid': self.env.user.id,
            'refund_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid':self.env.user.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

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

    def action_sync_price(self):
        provider_type_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa')
        pricing_obj = self.env['tt.pricing.agent'].sudo()

        pricelist_data = {}
        price_list = []

        # buat adjustment pricing per pax
        for psg in self.passenger_ids:
            base_price = 0
            base_comm = 0
            base_fixed = 0

            """ Hitung base_price, base_comm & base_fixed """
            for scs in psg.passenger_id.cost_service_charge_ids:  # get base price dari service charge psg
                if scs.charge_type == 'TOTAL':
                    base_price += scs.amount
                if scs.charge_type == 'RAC':
                    if scs.charge_code == 'fixed':
                        base_fixed += scs.amount
                    else:
                        base_comm += scs.amount

            """ Hitung base price, comm & fixed dari pricelist """
            base_pricelist_price = psg.passenger_id.pricelist_id.sale_price
            base_pricelist_fixed = psg.passenger_id.pricelist_id.cost_price - psg.passenger_id.pricelist_id.nta_price
            base_pricelist_comm = psg.passenger_id.pricelist_id.commission_price

            """ Jika harga fare di booking tidak sama dengan di pricelist """
            if base_price != base_pricelist_price:
                price_list.append({
                    'amount': base_pricelist_price - base_price,
                    'total': base_pricelist_price - base_price,
                    'pax_count': 1,
                    'pax_type': psg.pax_type,
                    'charge_code': 'sync_fare',
                    'charge_type': 'TOTAL',
                    'pricelist_id': psg.passenger_id.pricelist_id.id,
                    'passenger_visa_id': psg.passenger_id.id
                })

            """ Jika total commission di booking tidak sama dengan di pricelist """
            if abs(base_comm) != abs(base_pricelist_comm):
                commission_list = pricing_obj.get_commission(abs(abs(base_pricelist_comm) - abs(base_comm)), self.agent_id,
                                                             provider_type_id)

                for comm in commission_list:
                    vals_comm = {
                        'pax_count': 1,
                        'pax_type': psg.pax_type,
                        'charge_code': 'sync_' + comm['code'],
                        'charge_type': 'RAC',
                        'pricelist_id': psg.passenger_id.pricelist_id.id,
                        'passenger_visa_id': psg.passenger_id.id
                    }

                    if abs(base_pricelist_comm) > abs(base_comm):
                        vals_comm.update({
                            'amount': -comm['amount'],
                            'total': comm['amount'],
                        })
                    else:
                        vals_comm.update({
                            'amount': -comm['amount'],
                            'total': comm['amount'],
                        })

                    price_list.append(vals_comm)

            """ Jika comm fixed di booking tidak sama dengan di pricelist """
            if abs(base_fixed) != base_pricelist_fixed:
                price_list.append({
                    'amount': base_pricelist_fixed - base_fixed,
                    'total': base_pricelist_fixed - base_fixed,
                    'pax_count': 1,
                    'pax_type': psg.pax_type,
                    'charge_code': 'sync_fixed',
                    'charge_type': 'RAC',
                    'pricelist_id': psg.passenger_id.pricelist_id.id,
                    'passenger_visa_id': psg.passenger_id.id
                })

        price_list2 = []
        # susun daftar ssc yang sudah dibuat
        for ssc in price_list:
            # compare with ssc_list
            ssc_same = False
            for ssc_2 in price_list2:
                if ssc['pricelist_id'] == ssc_2['pricelist_id']:
                    if ssc['charge_code'] == ssc_2['charge_code']:
                        if ssc['pax_type'] == ssc_2['pax_type']:
                            ssc_same = True
                            # update ssc_final
                            ssc_2['pax_count'] = ssc_2['pax_count'] + 1,
                            ssc_2['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                            ssc_2['total'] += ssc.get('amount')
                            ssc_2['pax_count'] = ssc_2['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'passenger_visa_ids': [],
                    # 'description': ssc['description'],
                    'pax_type': ssc['pax_type'],
                    # 'currency_id': ssc['currency_id'],
                    'pax_count': 1,
                    'total': ssc['total'],
                    'pricelist_id': ssc['pricelist_id']
                }
                if 'commission_agent_id' in ssc:
                    vals.update({
                        'commission_agent_id': ssc['commission_agent_id']
                    })
                vals['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                price_list2.append(vals)

        self.create_service_charge(price_list2)

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

    def create_ticket_api(self, passengers):
        ticket_list = []
        ticket_found = []
        ticket_not_found = []
        #################
        for passenger in self.booking_id.passenger_ids:
            passenger.is_ticketed = False
        #################
        for psg in passengers:
            psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() ==
                                                                       ('%s%s' % (psg.get('first_name', ''),
                                                                                  psg.get('last_name',
                                                                                          ''))).lower().replace(' ',
                                                                                                                ''))

            if not psg_obj:
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() * 2 ==
                                                                           ('%s%s' % (psg.get('first_name', ''),
                                                                                      psg.get('last_name',
                                                                                              ''))).lower().replace(' ',
                                                                                                                    ''))
            if psg_obj:
                _logger.info(json.dumps(psg_obj.ids))
                if len(psg_obj.ids) > 1:
                    for psg_o in psg_obj:
                        if not psg_o.is_ticketed:
                            psg_obj = psg_o
                            break
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': '',
                    'passenger_id': psg_obj.id
                }))
                psg_obj.is_ticketed = True
                ticket_found.append(psg_obj.id)
            else:
                ticket_not_found.append(psg)

        self.write({
            'ticket_ids': ticket_list
        })
