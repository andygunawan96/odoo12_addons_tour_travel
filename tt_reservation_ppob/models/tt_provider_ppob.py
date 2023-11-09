from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools.db_connector import GatewayConnector
from ...tools import variables
from datetime import datetime
from datetime import datetime, timedelta
import json, logging

_logger = logging.getLogger(__name__)


class TtProviderPPOB(models.Model):
    _name = 'tt.provider.ppob'
    _rec_name = 'pnr'
    # _order = 'departure_date'
    _description = 'Provider PPOB'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    original_pnr = fields.Char('Original PNR')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.ppob', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    balance_due = fields.Float('Balance Due')
    total_price = fields.Float('Total Price')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Product')
    carrier_code = fields.Char('Product Code')
    carrier_name = fields.Char('Product Name')
    session_id = fields.Char('Session ID', readonly=True, states={'draft': [('readonly', False)]})
    payment_session_id = fields.Char('Payment Session ID', readonly=True, states={'draft': [('readonly', False)]})
    customer_number = fields.Char('Customer Number', readonly=True, states={'draft': [('readonly', False)]})
    customer_name = fields.Char('Customer Name', readonly=True, states={'draft': [('readonly', False)]})
    customer_id_number = fields.Char('Customer ID', readonly=True, states={'draft': [('readonly', False)]})
    game_zone_id = fields.Char('Customer Game Zone ID', readonly=True, states={'draft': [('readonly', False)]})
    unit_code = fields.Char('Unit Code', readonly=True, states={'draft': [('readonly', False)]})
    unit_name = fields.Char('Unit Name', readonly=True, states={'draft': [('readonly', False)]})
    unit_phone_number = fields.Char('Unit Phone Number', readonly=True, states={'draft': [('readonly', False)]})
    unit_address = fields.Char('Unit Address', readonly=True, states={'draft': [('readonly', False)]})
    fare_type = fields.Char('Fare Type', readonly=True, states={'draft': [('readonly', False)]})
    power = fields.Integer('Power', readonly=True, states={'draft': [('readonly', False)]})
    is_family = fields.Boolean('Is Family', readonly=True, states={'draft': [('readonly', False)]})
    registration_number = fields.Char('Registration Number', readonly=True, states={'draft': [('readonly', False)]})
    registration_date = fields.Date('Registration Date', readonly=True, states={'draft': [('readonly', False)]})
    bill_expired_date = fields.Date('Bill Expired Date', readonly=True, states={'draft': [('readonly', False)]})
    is_send_transaction_code = fields.Boolean('Send Transaction Code', default=False, readonly=True)
    transaction_code = fields.Char('Transaction Code', readonly=True, states={'draft': [('readonly', False)]})
    transaction_name = fields.Char('Transaction Name', readonly=True, states={'draft': [('readonly', False)]})
    meter_number = fields.Char('Meter Number', readonly=True, states={'draft': [('readonly', False)]})
    distribution_code = fields.Char('Distribution Code', readonly=True, states={'draft': [('readonly', False)]})
    max_kwh = fields.Float('Max KWH', readonly=True, states={'draft': [('readonly', False)]})
    payment_message = fields.Text('Payment Message', readonly=True)
    allowed_denomination_ids = fields.Many2many('tt.master.nominal.ppob', 'reservation_ppob_nominal_rel', 'provider_booking_id',
                                                'nominal_id', string='Allowed Denominations', readonly=True,
                                                states={'draft': [('readonly', False)]})
    total = fields.Monetary('Total Bill Amount', readonly=True, default=0)
    ppob_bill_ids = fields.One2many('tt.bill.ppob', 'provider_booking_id', string='Bills', readonly=True,
                                    states={'draft': [('readonly', False)]})
    ppob_bill_detail_ids = fields.One2many('tt.bill.detail.ppob', 'provider_booking_id', string='Bill Details', readonly=True,
                                    states={'draft': [('readonly', False)]})
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_ppob_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    promotion_code = fields.Char(string='Promotion Code')
    unpaid_bill = fields.Integer(string='Unpaid Bill Amount')
    unpaid_bill_display = fields.Integer(string='Unpaid Bill Displayed')
    raw_additional_data = fields.Text('Raw Additional Data')
    ticket_ids = fields.One2many('tt.ticket.ppob', 'provider_id', 'Ticket Number')

    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Char('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    cancel_uid = fields.Many2one('res.users', 'Cancel By')
    cancel_date = fields.Datetime('Cancel Date')
    #
    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    error_history_ids = fields.One2many('tt.reservation.err.history','res_id','Error History', domain=[('res_model','=','tt.provider.ppob')])
    # , domain = [('res_model', '=', 'tt.provider.ppob')]

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    ##button function
    def action_set_to_issued_from_button(self, payment_data={}):
        if self.state == 'issued':
            raise UserError("Has been Issued.")
        self.write({
            'state': 'issued',
            'issued_uid': self.env.user.id,
            'issued_date': datetime.now()
        })
        self.booking_id.check_provider_state({'co_uid': self.env.user.id}, [], False, payment_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_force_issued_from_button(self, payment_data={}):
        if self.state == 'issued':
            raise UserError("Has been Issued.")

        # set PNR disini karena sebelum create ledger harus ada PNRnya, kalau set to issued antara ledger sudah pernah ke create atau tidak ada ledger
        if not self.pnr and self.booking_id:
            self.write({
                'pnr': self.booking_id.name
            })

        req = {
            'book_id': self.booking_id.id,
            'member': payment_data.get('member'),
            'acquirer_seq_id': payment_data.get('acquirer_seq_id'),
            'pin': payment_data.get('pin')
        }
        context = {
            'co_agent_id': self.booking_id.agent_id.id,
            'co_agent_type_id': self.booking_id.agent_type_id.id,
            'co_uid': self.env.user.id
        }
        payment_res = self.booking_id.payment_reservation_api('ppob',req,context)
        if payment_res['error_code'] != 0:
            raise UserError(payment_res['error_msg'])


        # balance_res = self.env['tt.agent'].check_balance_limit_api(self.booking_id.agent_id.id,self.booking_id.agent_nta)
        # if balance_res['error_code'] != 0:
        #     raise UserError("Balance not enough.")
        #
        # self.action_create_ledger(self.env.user.id)
        self.action_set_to_issued_from_button(payment_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 261')
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

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

        try:
            data = {
                'code': 9901,
                'title': 'PROVIDER PPOB REVERSE LEDGER',
                'message': 'Provider Ledger reversed from button: %s (%s)\nUser: %s\n' % (
                self.booking_id.name, self.pnr, self.env.user.name)
            }
            context = {
                "co_ho_id": self.booking_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "reverse provider ledger" telegram notification: ' + str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_set_to_book_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 262')
        if self.state == 'booked':
            raise UserError("Has been Booked.")

        self.write({
            'state': 'booked',
            'booked_uid': self.env.user.id,
            'booked_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid':self.env.user.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reverse_ledger(self):
        for rec in self.booking_id.ledger_ids:
            pnr_text = self.pnr if self.pnr else str(self.sequence)
            if rec.pnr == pnr_text and not rec.is_reversed:
                rec.reverse_ledger()

        for rec in self.cost_service_charge_ids:
            rec.is_ledger_created = False

    def action_booked_api_ppob(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'pnr2': provider_data['pnr2'],
                'original_pnr': provider_data['original_pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
                'hold_date': datetime.today() + timedelta(hours=1),
                'balance_due': provider_data['balance_due']
            })

    def action_issued_api_ppob(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
                'balance_due': 0
            })

    def action_cancel_api_ppob(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_cancel_pending_api_ppob(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_failed_booked_api_ppob(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_booked',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_issued_api_ppob(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_issued',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_paid_api_ppob(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_paid',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_void_api_ppob(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'void_failed',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_expired(self):
        self.state = 'cancel2'

    def action_cancel(self):
        self.cancel_date = fields.Datetime.now()
        self.cancel_uid = self.env.user.id
        self.state = 'cancel'

    def update_status_api_ppob(self, data, context):
        for rec in self:
            if data.get('fail_state'):
                if data['fail_state'] == 'fail_issued':
                    error_dat = data['error_data']
                    rec.action_failed_issued_api_ppob(error_dat['error_code'], error_dat['error_msg'])
                    # rec.action_reverse_ledger_from_button()
                elif data['fail_state'] == 'fail_paid':
                    error_dat = data['error_data']
                    rec.action_failed_paid_api_ppob(error_dat['error_code'], error_dat['error_msg'])
            else:
                if rec.state != 'issued':
                    # if any(not rec2.is_ledger_created for rec2 in rec.cost_service_charge_ids):
                    #     payment_req = {
                    #         'book_id': rec.booking_id.id,
                    #         'member': rec.booking_id.is_member,
                    #         'acquirer_seq_id': rec.booking_id.payment_method,
                    #     }
                    #     payment_res = rec.booking_id.payment_reservation_api('ppob', payment_req, context)
                    #     if payment_res['error_code'] != 0:
                    #         raise UserError(payment_res['error_msg'])

                    rec.sudo().write({
                        'pnr': data['session_id'],
                        'pnr2': data['vendor_pnr'],
                        'original_pnr': data['pnr'],
                        'payment_message': data['message'],
                    })

                    for rec2 in rec.booking_id.ledger_ids:
                        if str(rec2.pnr) == str(rec.sequence):
                            rec2.sudo().write({
                                'pnr': data['session_id']
                            })

                    for rec2 in rec.cost_service_charge_ids:
                        rec2.sudo().write({
                            'description': data['session_id']
                        })

                    if data.get('bill_data'):
                        for rec2 in data['bill_data']:
                            bill_obj = self.env['tt.bill.ppob'].sudo().search([('provider_booking_id', '=', int(rec.id)), ('period', '=', datetime.strptime(rec2['period'], '%Y%m'))], limit=1)
                            if bill_obj:
                                new_bill_vals = {
                                    'stamp_fee': rec2.get('stamp_fee') and rec2['stamp_fee'] or 0,
                                    'ppn_tax_amount': rec2.get('ppn_tax_amount') and rec2['ppn_tax_amount'] or 0,
                                    'ppj_tax_amount': rec2.get('ppj_tax_amount') and rec2['ppj_tax_amount'] or 0,
                                    'installment': rec2.get('installment') and rec2['installment'] or 0,
                                    'fare_amount': rec2.get('fare_amount') and rec2['fare_amount'] or 0,
                                    'kwh_amount': rec2.get('kwh_amount') and rec2['kwh_amount'] or 0,
                                    'token': rec2.get('token') and rec2['token'] or ''
                                }
                                if not bill_obj[0].admin_fee and rec2.get('admin_fee'):
                                    new_bill_vals.update({
                                        'admin_fee': rec2['admin_fee']
                                    })
                                bill_obj[0].sudo().write(new_bill_vals)

                    rec.action_issued_api_ppob(context)

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            # update 19 Feb 2020 maximum per pax sesuai dengan pax_count dari service charge
            # scs['pax_count'] = 0
            scs_pax_count = 0
            scs['passenger_ppob_ids'] = []
            scs['total'] = 0
            scs['currency_id'] = currency_obj.get_id(scs.get('currency'),default_param_idr=True)
            scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'),default_param_idr=True)
            scs['provider_ppob_booking_id'] = self.id
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    scs['passenger_ppob_ids'].append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    scs['total'] += scs['amount']
            scs['passenger_ppob_ids'] = [(6,0,scs['passenger_ppob_ids'])]
            scs['ho_id'] = self.booking_id.ho_id.id if self.booking_id and self.booking_id.ho_id else ''
            service_chg_obj.create(scs)

        # "sequence": 1,
        # "charge_code": "fare",
        # "charge_type": "FARE",
        # "currency": "IDR",
        # "amount": 4800000,
        # "foreign_currency": "IDR",
        # "foreign_amount": 4800000,
        # "pax_count": 3,
        # "pax_type": "ADT",
        # "total": 14400000

    def delete_service_charge(self):
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created
    # @api.depends('cost_service_charge_ids')
    # def _compute_total(self):
    #     for rec in self:
    #         total = 0
    #         total_orig = 0
    #         for sc in rec.cost_service_charge_ids:
    #             if sc.charge_code.find('r.ac') < 0:
    #                 total += sc.total
    #             # total_orig adalah NTA
    #             total_orig += sc.total
    #         rec.write({
    #             'total': total,
    #             'total_orig': total_orig
    #         })

    def action_create_ledger(self,issued_uid,pay_method=None, use_point=False,payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self,issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)
        # else:
        #     raise UserError("Cannot create ledger, ledger has been created before.")

    def create_ticket_api(self,passengers):
        ticket_list = []
        ticket_found = []
        ticket_not_found = []
        for psg in passengers:
            psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() ==
                                                                ('%s%s' % (psg.get('first_name', ''),
                                                                           psg.get('last_name', ''))).lower().replace(' ',''))

            if not psg_obj:
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower()*2 ==
                                                                           ('%s%s' % (psg.get('first_name', ''),
                                                                                      psg.get('last_name',
                                                                                              ''))).lower().replace(' ',''))
            if psg_obj:
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': '',
                    'passenger_id': psg_obj.id
                }))
                ticket_found.append(psg_obj.id)
            else:
                ticket_not_found.append(psg)

        self.write({
            'ticket_ids': ticket_list
        })

    def prepaid_update_service_charge(self, passenger_vals, service_charge_vals):
        ledger_created = self.delete_service_charge()
        if ledger_created:
            self.action_reverse_ledger()
            self.delete_service_charge()

        self.create_ticket_api(passenger_vals)
        self.create_service_charge(service_charge_vals)

    def get_description(self):
        desc = ''
        if self.carrier_id.code == 'pln_postpaid':
            desc += 'Fare Type: %s <br/>' % (self.fare_type,)
            desc += 'Power: %s <br/>' % (self.power,)
            for rec in self.ppob_bill_ids:
                if rec.meter_history_ids:
                    desc += 'Meter (%s): %s <br/>' % (rec.period.strftime('%b %Y'), rec.meter_history_ids[-1].after_meter)
        elif self.carrier_id.code == 'pln_prepaid':
            desc += 'Fare Type: %s <br/>' % (self.fare_type,)
            desc += 'Power: %s <br/>' % (self.power,)
            for rec in self.ppob_bill_ids:
                desc += 'Token (%s): %s <br/>' % (rec.period.strftime('%b %Y'), rec.token)
                desc += 'KWH Amount (%s): %s <br/>' % (rec.period.strftime('%b %Y'), rec.kwh_amount)
        elif self.carrier_id.code == 'pln_nontag':
            desc += 'Transaction: %s <br/>' % (self.transaction_name,)
        elif self.carrier_id.code == 'bpjs_kesehatan':
            desc += ''
        return desc

    def to_dict(self):
        bill_list = []
        for rec in self.ppob_bill_ids:
            bill_list.append(rec.to_dict())

        bill_detail_list = []
        for rec in self.ppob_bill_detail_ids:
            bill_detail_list.append(rec.to_dict())

        service_charges = []
        for rec in self.cost_service_charge_ids:
            if rec.charge_type == 'RAC' and not rec.charge_code == 'rac':
                continue
            service_charges.append(rec.to_dict())

        allowed_denominations = []
        for rec in self.allowed_denomination_ids:
            allowed_denominations.append({
                'currency': rec.currency_id.name,
                'nominal': rec.nominal,
            })

        ticket_list = []

        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'original_pnr': self.original_pnr and self.original_pnr or '',
            'provider': self.provider_id and self.provider_id.code or '',
            'provider_id': self.id,
            'agent_id': self.booking_id.agent_id.id if self.booking_id and self.booking_id.agent_id else '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'payment_message': self.payment_message and self.payment_message or '',
            'balance_due': self.balance_due and self.balance_due or 0,
            'total_price': self.total_price and self.total_price or 0,
            'bill_data': bill_list,
            'bill_details': bill_detail_list,
            'currency': self.currency_id and self.currency_id.name or '',
            'error_msg': self.error_history_ids and self.error_history_ids[-1].error_msg or '',
            # 'service_charges': service_charges,
            'carrier_name': self.carrier_id and self.carrier_id.name or '',
            'carrier_code': self.carrier_code and self.carrier_code or '',
            'fare_type': self.fare_type and self.fare_type or '',
            'max_kwh': self.max_kwh and self.max_kwh or 0,
            'customer_number': self.customer_number and self.customer_number or '',
            'customer_name': self.customer_name and self.customer_name or '',
            'customer_id_number': self.customer_id_number and self.customer_id_number or '',
            'game_zone_id': self.game_zone_id and self.game_zone_id or '',
            'unit_code': self.unit_code and self.unit_code or '',
            'unit_name': self.unit_name and self.unit_name or '',
            'unit_phone_number': self.unit_phone_number and self.unit_phone_number or '',
            'unit_address': self.unit_address and self.unit_address or '',
            'power': self.power and self.power or 0,
            'is_family': self.is_family and self.is_family or False,
            'registration_number': self.registration_number and self.registration_number or '',
            'registration_date': self.registration_date and self.registration_date.strftime('%Y-%m-%d') or '',
            'bill_expired_date': self.bill_expired_date and self.bill_expired_date.strftime('%Y-%m-%d') or '',
            'is_send_transaction_code': self.is_send_transaction_code and self.is_send_transaction_code or '',
            'transaction_code': self.transaction_code and self.transaction_code or '',
            'transaction_name': self.transaction_name and self.transaction_name or '',
            'meter_number': self.meter_number and self.meter_number or '',
            'distribution_code': self.distribution_code and self.distribution_code or '',
            'unpaid_bill': self.unpaid_bill and self.unpaid_bill or 0,
            'unpaid_bill_display': self.unpaid_bill_display and self.unpaid_bill_display or 0,
            'session_id': self.session_id and self.session_id or '',
            'raw_additional_data': self.raw_additional_data and self.raw_additional_data or '',
            'allowed_denominations': allowed_denominations,
            'description': self.get_description(),
            'tickets': ticket_list
        }

        return res

    # def get_cost_service_charges(self):
    #     sc_value = {}
    #     for p_sc in self.cost_service_charge_ids:
    #         p_charge_type = p_sc.charge_type
    #         p_pax_type = p_sc.pax_type
    #         if p_charge_type == 'RAC' and p_sc.charge_code !=  'rac':
    #             continue
    #         if not sc_value.get(p_pax_type):
    #             sc_value[p_pax_type] = {}
    #         if not sc_value[p_pax_type].get(p_charge_type):
    #             sc_value[p_pax_type][p_charge_type] = {}
    #             sc_value[p_pax_type][p_charge_type].update({
    #                 'amount': 0,
    #                 'foreign_amount': 0
    #             })
    #         sc_value[p_pax_type][p_charge_type].update({
    #             'charge_code': p_sc.charge_code,
    #             'currency': p_sc.currency_id.name,
    #             'pax_count': p_sc.pax_count,
    #             'total': p_sc.total,
    #             'foreign_currency': p_sc.foreign_currency_id.name,
    #             'amount': sc_value[p_pax_type][p_charge_type]['amount'] + p_sc.amount,
    #             'foreign_amount': sc_value[p_pax_type][p_charge_type]['foreign_amount'] + p_sc.foreign_amount,
    #         })
    #     return sc_value
