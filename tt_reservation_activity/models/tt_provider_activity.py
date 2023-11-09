from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools.db_connector import GatewayConnector
from ...tools import variables
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class TtProviderActivity(models.Model):
    _name = 'tt.provider.activity'
    _rec_name = 'pnr'
    _description = 'Provider Activity'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier')
    carrier_code = fields.Char('Carrier Code')
    carrier_name = fields.Char('Carrier Name')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.activity', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    balance_due = fields.Float('Balance Due')
    total_price = fields.Float('Total Price')
    activity_detail_ids = fields.One2many('tt.reservation.activity.details', 'provider_booking_id', 'Reservation Details')

    sid_issued = fields.Char('SID Issued')#signature generate sendiri

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_activity_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    # total = fields.Monetary(string='Total', readonly=True)
    # total_fare = fields.Monetary(string='Total Fare', compute="_compute_provider_total_fare", readonly=True)
    # total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    promotion_code = fields.Char(string='Promotion Code')


    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Char('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    #
    # refund_uid = fields.Many2one('res.users', 'Refund By')
    # refund_date = fields.Datetime('Refund Date')
    ticket_ids = fields.One2many('tt.ticket.activity', 'provider_id', 'Ticket Number')

    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    error_history_ids = fields.One2many('tt.reservation.err.history', 'res_id', 'Error History', domain=[('res_model', '=', 'tt.provider.activity')])

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
        payment_res = self.booking_id.payment_reservation_api('activity', req, context)
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

    def action_set_to_book_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 99')
        if self.state == 'booked':
            raise UserError("Has been Booked.")

        self.write({
            'state': 'booked',
            'booked_uid': self.env.user.id,
            'booked_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid': self.env.user.id})

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

    def action_reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 102')
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

        # if not self.is_ledger_created:
        #     raise UserError("This Provider Ledger is not Created.")

        ##fixme salahhh, ini ke reverse semua provider bukan provider ini saja
        for rec in self.booking_id.ledger_ids:
            if rec.pnr == self.pnr and not rec.is_reversed:
                rec.reverse_ledger()

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
                'title': 'PROVIDER ACTIVITY REVERSE LEDGER',
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

    def action_booked_api_activity(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data.get('code') and provider_data['code'] or '',
                'pnr2': provider_data.get('uuid') and provider_data['uuid'] or '',
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
            for rec2 in rec.cost_service_charge_ids:
                rec2.write({
                    'description': provider_data['code']
                })

    def action_issued_api_activity(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
                'balance_due': 0
            })

    def action_cancel_api_activity(self, context):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_cancel_pending_api_activity(self, context):
        for rec in self:
            rec.write({
                'state': 'cancel_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_failed_booked_api_activity(self, err_code, err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_booked',
                'error_history_ids': [(0, 0, {
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_issued_api_activity(self, err_code, err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_issued',
                'error_history_ids': [(0, 0, {
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_paid_api_activity(self, err_code, err_msg):
        for rec in self:
            rec.write({
                'state': 'fail_paid',
                'error_history_ids': [(0, 0, {
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_void_api_activity(self, err_code, err_msg):
        for rec in self:
            rec.write({
                'state': 'void_failed',
                'error_history_ids': [(0, 0, {
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

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

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
                    'ticket_number': psg.get('ticket_number'),
                    'passenger_id': psg_obj.id
                }))
                ticket_found.append(psg_obj.id)
            else:
                ticket_not_found.append(psg)

        psg_with_no_ticket = self.booking_id.passenger_ids.filtered(lambda x: x.id not in ticket_found)
        for idx, psg in enumerate(ticket_not_found):
            ticket_list.append((0, 0, {
                'pax_type': psg.get('pax_type'),
                'ticket_number': psg.get('ticket_number', ''),
                'passenger_id': psg_with_no_ticket[idx].id
            }))

        self.write({
            'ticket_ids': ticket_list
        })

    def update_ticket_api(self,passengers):##isi ticket number
        ticket_not_found = []
        for psg in passengers:
            ticket_found = False
            for ticket in self.ticket_ids:
                psg_name = ticket.passenger_id.name.replace(' ','').lower()
                if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ','').lower() in [psg_name, psg_name*2]:
                    ticket.write({
                        'ticket_number': psg.get('ticket_number','')
                    })
                    ticket_found = True
                    break
            if not ticket_found:
                ticket_not_found.append(psg)

        for psg in ticket_not_found:
            self.write({
                'ticket_ids': [(0,0,{
                    'ticket_number': psg.get('ticket_number', ''),
                    'pax_type': psg.get('pax_type'),
                })]
            })

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            # update 19 Feb 2020 maximum per pax sesuai dengan pax_count dari service charge
            # scs['pax_count'] = 0
            # April 28, 2020 - SAM
            currency_id = currency_obj.get_id(scs.get('currency'), default_param_idr=True)
            foreign_currency_id = currency_obj.get_id(scs.get('foreign_currency'), default_param_idr=True)
            scs_pax_count = 0
            total = 0
            # scs['passenger_activity_ids'] = []
            # scs['total'] = 0
            # scs['currency_id'] = currency_obj.get_id(scs.get('currency'),default_param_idr=True)
            # scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'),default_param_idr=True)
            # scs['provider_activity_booking_id'] = self.id
            passenger_activity_ids = []
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    # scs['passenger_activity_ids'].append(psg.passenger_id.id)
                    passenger_activity_ids.append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    # scs['total'] += scs['amount']
                    total += scs['amount']
            scs.update({
                'passenger_activity_ids': [(6, 0, passenger_activity_ids)],
                'total': total,
                'currency_id': currency_id,
                'foreign_currency_id': foreign_currency_id,
                'provider_activity_booking_id': self.id,
                'description': self.pnr and self.pnr or str(self.sequence),
                'ho_id': self.booking_id.ho_id.id if self.booking_id and self.booking_id.ho_id else ''
            })
            scs.pop('currency')
            scs.pop('foreign_currency')
            # scs['passenger_activity_ids'] = [(6,0,scs['passenger_activity_ids'])]
            # scs['description'] = self.pnr
            # END
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

    def action_create_ledger(self,issued_uid, pay_method=None, use_point=False,payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)

    def to_dict(self):
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())
        activity_details_list = []
        for rec in self.activity_detail_ids:
            activity_details_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id and self.provider_id.code or '',
            'provider_id': self.id,
            'error_msg': self.error_history_ids and self.error_history_ids[-1].error_msg or '',
            'carrier_name': self.carrier_id and self.carrier_id.name or '',
            'carrier_code': self.carrier_id and self.carrier_id.code or '',
            'agent_id': self.booking_id.agent_id.id if self.booking_id and self.booking_id.agent_id else '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'balance_due': self.balance_due and self.balance_due or 0,
            'total_price': self.total_price and self.total_price or 0,
            'currency': self.currency_id and self.currency_id.name or '',
            'activity_details': activity_details_list,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
        }

        return res

    def get_carrier_name(self):
        return []
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
