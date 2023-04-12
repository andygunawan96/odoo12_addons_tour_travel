from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime

STATE_PASSPORT = [
    ('fail_booked', 'Failed (Book)'),
    ('draft', 'Open'),
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
    ('done', 'Done')
]


class ProviderPassportPassengers(models.Model):
    _name = 'tt.provider.passport.passengers'
    _description = 'Provider Passport Passengers'

    provider_id = fields.Many2one('tt.provider.passport', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passport.order.passengers', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Passport Pricelist')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
        }
        return res


class TtProviderPassport(models.Model):
    _name = 'tt.provider.passport'
    _rec_name = 'pnr'
    _description = 'Provider Passport'

    pnr = fields.Char('PNR')  # di isi aja order number
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.passport', 'Order Number', ondelete='cascade')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], related='booking_id.ho_id')
    agent_id = fields.Many2one('tt.agent', 'Agent', related='booking_id.agent_id')
    passport_id = fields.Many2one('tt.reservation.passport.pricelist', 'Passport Pricelist')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    state_passport = fields.Selection(STATE_PASSPORT, 'State', related="booking_id.state_passport")
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_passport_booking_id',
                                              'Cost Service Charges')

    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')

    in_process_date = fields.Datetime('In Process Date', readonly=1)

    done_date = fields.Datetime('Done Date', readonly=1)
    hold_date = fields.Datetime('Hold Date', readonly=1)
    expired_date = fields.Datetime('Expired Date', readonly=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    vendor_ids = fields.One2many('tt.reservation.passport.vendor.lines', 'provider_id', 'Expenses')

    passenger_ids = fields.One2many('tt.provider.passport.passengers', 'provider_id', 'Passengers')

    total_price = fields.Float('Total Price', default=0)

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##
    def action_booked_api_passport(self, provider_data, api_context, hold_date):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
                'hold_date': hold_date,
            })

    def action_issued_api_passport(self, context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
            })

    def action_fail_booked_passport(self):
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
        """ Fungsi ini mengembalikan state provider ke booked & state passport ke validate """
        """ Fungsi ini dijalankan, in case terdapat salah input harga di pricelist & sudah potong ledger """

        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 216')

        self.action_booked()  # ubah ke booked

        # ubah state passport ke validate
        self.booking_id.state = 'validate'

        # ubah state pax passport ke validate
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

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['pax_count'] = 0  # jumlah pax
            scs['total'] = 0  # total pricing
            scs['passenger_passport_ids'] = []
            scs['currency_id'] = currency_obj.get_id('IDR')  # currency (IDR)
            scs['foreign_currency_id'] = currency_obj.get_id('IDR')  # currency (foreign)
            scs['provider_passport_booking_id'] = self.id  # id provider passport
            if scs['charge_code'] != 'disc':
                for psg in self.passenger_ids:
                    if scs['pax_type'] == psg.pax_type and scs['passport_pricelist_id'] == psg.pricelist_id.id:
                        scs['passenger_passport_ids'].append(psg.passenger_id.id)  # add passenger to passenger passport ids
                        scs['pax_count'] += 1
                        scs['total'] += scs['amount']
            else:
                for psg in self.passenger_ids:
                    scs['passenger_passport_ids'].append(psg.passenger_id.id)  # add passenger to passenger passport ids
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
            scs['passenger_passport_ids'] = [(6, 0, scs['passenger_passport_ids'])]
            if 'commission_agent_id' in scs:
                scs['commission_agent_id'] = scs['commission_agent_id']
            scs['description'] = self.pnr and self.pnr or ''
            if scs['total'] != 0:
                service_chg_obj.create(scs)

    def delete_service_charge(self):
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees is False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created

    def action_create_ledger(self, issued_uid, pay_method=None, use_point=False,payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)

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
        printout_expenses_id = self.env.ref('tt_report_common.action_create_expenses_invoice_passport')
        return printout_expenses_id.report_action(self, data=datas)

    def action_sync_price(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 217')
        provider_type_id = self.env.ref('tt_reservation_passport.tt_provider_type_passport')
        pricing_obj = self.env['tt.pricing.agent'].sudo()

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
                    'passenger_passport_id': psg.passenger_id.id
                })

            """ Jika total commission di booking tidak sama dengan di pricelist """
            if abs(base_comm) != abs(base_pricelist_comm):
                commission_list = pricing_obj.get_commission(abs(abs(base_pricelist_comm) - abs(base_comm)), self.agent_id,
                                                             provider_type_id)  # pembagian komisi lagi

                for comm in commission_list:
                    vals_comm = {
                        'pax_count': 1,
                        'pax_type': psg.pax_type,
                        'charge_code': 'sync_' + comm['code'],
                        'charge_type': 'RAC',
                        'pricelist_id': psg.passenger_id.pricelist_id.id,
                        'passenger_passport_id': psg.passenger_id.id
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
            if abs(base_fixed) != abs(base_pricelist_fixed):
                price_list.append({
                    'amount': base_pricelist_fixed - base_fixed,
                    'total': base_pricelist_fixed - base_fixed,
                    'pax_count': 1,
                    'pax_type': psg.pax_type,
                    'charge_code': 'sync_fixed',
                    'charge_type': 'RAC',
                    'pricelist_id': psg.passenger_id.pricelist_id.id,
                    'passenger_passport_id': psg.passenger_id.id
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
                            ssc_2['passenger_passport_ids'].append(ssc['passenger_passport_id'])
                            ssc_2['total'] += ssc.get('amount')
                            ssc_2['pax_count'] = ssc_2['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'passenger_passport_ids': [],
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
                vals['passenger_passport_ids'].append(ssc['passenger_passport_id'])
                price_list2.append(vals)

        self.create_service_charge(price_list2)

    def to_dict(self):
        passenger_list = []
        for rec in self.passenger_ids:
            passenger_list.append(rec.to_dict())
        vendor_list = []
        for rec in self.vendor_ids:
            vendor_list.append(rec.to_dict())
        ticket_list = []
        res = {
            'pnr': self.pnr and self.pnr or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'passengers': passenger_list,
            'vendors': vendor_list,
            'tickets': ticket_list
        }
        return res

    def get_carrier_name(self):
        return []
