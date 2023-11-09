from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools.db_connector import GatewayConnector
from ...tools import variables
from datetime import datetime
from datetime import datetime, timedelta
import json, logging, pytz

_logger = logging.getLogger(__name__)

class TtProviderMitraKeluarga(models.Model):
    _name = 'tt.provider.mitrakeluarga'
    _inherit = 'tt.history'
    _rec_name = 'pnr'
    # _order = 'departure_date'
    _description = 'Provider swab express'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.mitrakeluarga', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    balance_due = fields.Float('Balance Due')
    total_price = fields.Float('Total Price')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Product')
    carrier_code = fields.Char('Product Code')
    carrier_name = fields.Char('Product Name')
    ticket_ids = fields.One2many('tt.ticket.mitrakeluarga', 'provider_id', 'Ticket Number')

    sid_issued = fields.Char('SID Issued', readonly=True,
                             states={'draft': [('readonly', False)]})  # signature generate sendiri
    sid_cancel = fields.Char('SID Cancel', readonly=True,
                             states={'draft': [('readonly', False)]})  # signature generate sendiri
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_mitrakeluarga_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Char('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    cancel_uid = fields.Many2one('res.users', 'Cancel By')
    cancel_date = fields.Datetime('Cancel Date')

    refund_uid = fields.Many2one('res.users', 'Refund By', readonly=True, states={'draft': [('readonly', False)]})
    refund_date = fields.Datetime('Refund Date', readonly=True, states={'draft': [('readonly', False)]})

    error_history_ids = fields.One2many('tt.reservation.err.history', 'res_id', 'Error History',
                                        domain=[('res_model', '=', 'tt.provider.mitrakeluarga')])

    additional_info = fields.Char('Additional Info', default=False)

    # reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines', 'Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    @api.model
    def create(self, vals_list):
        rec = super(TtProviderMitraKeluarga, self).create(vals_list)
        rec.write({
            'pnr': rec.booking_id.name,
            'pnr2': rec.booking_id.name
        })
        return rec

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
        payment_res = self.booking_id.payment_reservation_api('mitrakeluarga', req, context)
        if payment_res['error_code'] != 0:
            raise UserError(payment_res['error_msg'])

        self.action_set_to_issued_from_button(payment_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 184')
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

        for rec in self.booking_id.ledger_ids:
            if rec.pnr in [self.pnr, str(self.sequence)] and not rec.is_reversed:
                rec.reverse_ledger()

        for rec in self.cost_service_charge_ids:
            rec.is_ledger_created = False

        self.write({
            'state': 'fail_refunded',
            'refund_uid': self.env.user.id,
            'refund_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid': self.env.user.id})

        try:
            data = {
                'code': 9901,
                'title': 'PROVIDER MEDICAL REVERSE LEDGER',
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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 185')
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

    # def action_booked_api_mitrakeluarga(self, provider_data, api_context):
    #     for rec in self:
    #         rec.write({
    #             'pnr': provider_data['pnr'],
    #             'pnr2': provider_data['pnr2'],
    #             'state': 'booked',
    #             'booked_uid': api_context['co_uid'],
    #             'booked_date': fields.Datetime.now(),
    #             'hold_date': datetime.today() + timedelta(days=1),
    #             'balance_due': provider_data['balance_due']
    #         })

    def action_issued_api_mitrakeluarga(self, context):
        # current_wib_datetime = datetime.now(pytz.timezone('Asia/Jakarta'))
        # current_datetime = current_wib_datetime.astimezone(pytz.utc)
        # if '08:00' < str(current_wib_datetime.time())[:5] < '18:00':
        #     pending_date = current_datetime + timedelta(hours=1)
        # else:
        #     pending_date = current_datetime.replace(hour=3, minute=0) # UTC0, jam 10 pagi surabaya
        #     if current_datetime > pending_date:
        #         pending_date = pending_date+timedelta(days=1)

        for rec in self:
            rec.write({
                'state': 'issued',
                'sid_issued': context['signature'],
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'balance_due': 0
            })

    def action_issued_mitrakeluarga(self, co_uid):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': co_uid,
                # 'sid_issued': context['signature'], #issuednya yg di issued pending
            })

    def action_cancel_api_mitrakeluarga(self, context):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_cancel_pending_api_mitrakeluarga(self, context):
        for rec in self:
            rec.write({
                'state': 'cancel_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_failed_booked_api_mitrakeluarga(self, err_code, err_msg):
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

    def action_failed_issued_api_mitrakeluarga(self, err_code, err_msg):
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

    def action_failed_paid_api_mitrakeluarga(self, err_code, err_msg):
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

    def action_failed_void_api_mitrakeluarga(self, err_code, err_msg):
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

    def action_cancel(self, context=False):
        self.cancel_date = fields.Datetime.now()
        if context:
            self.cancel_uid = context['co_uid']
        else:
            self.cancel_uid = self.env.user.id
        self.state = 'cancel'

        ho_id = self.booking_id.agent_id.ho_id.id
        self.env['tt.mitrakeluarga.api.con'].send_cancel_order_notification(self.booking_id.name,
                                                                        self.env.user.name,
                                                                        self.booking_id.test_datetime.astimezone(
                                                                            pytz.timezone('Asia/Jakarta')).strftime(
                                                                            "%d-%m-%Y %H:%M"),
                                                                        self.booking_id.test_address, ho_id)

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            # update 19 Feb 2020 maximum per pax sesuai dengan pax_count dari service charge
            # scs['pax_count'] = 0
            scs_pax_count = 0
            scs['passenger_mitrakeluarga_ids'] = []
            scs['total'] = 0
            scs['currency_id'] = currency_obj.get_id(scs.get('currency'), default_param_idr=True)
            scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'), default_param_idr=True)
            scs['provider_mitrakeluarga_booking_id'] = self.id
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    scs['passenger_mitrakeluarga_ids'].append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    scs['total'] += scs['amount']
            scs['passenger_mitrakeluarga_ids'] = [(6, 0, scs['passenger_mitrakeluarga_ids'])]
            scs['description'] = self.pnr and self.pnr or str(self.sequence)
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


    def action_create_ledger(self, issued_uid, pay_method=None, use_point=False,payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)

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

    def to_dict(self):
        service_charges = []
        for rec in self.cost_service_charge_ids:
            if rec.charge_type == 'RAC' and not rec.charge_code == 'rac':
                continue
            service_charges.append(rec.to_dict())
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id and self.provider_id.code or '',
            'provider_id': self.id,
            'agent_id': self.booking_id.agent_id.id if self.booking_id and self.booking_id.agent_id else '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'balance_due': self.balance_due and self.balance_due or 0,
            'total_price': self.total_price and self.total_price or 0,
            'carrier_name': self.carrier_id and self.carrier_id.name or '',
            'carrier_code': self.carrier_id and self.carrier_id.code or '',
            'error_msg': self.error_history_ids and self.error_history_ids[-1].error_msg or '',
            'tickets': ticket_list,
            'additional_info': self.additional_info
        }

        return res

    def update_ticket_per_pax_api(self, idx, passenger_ticket):
        self.ticket_ids[idx].ticket_number = passenger_ticket
        self.ticket_ids[idx].passenger_id.ticket_number = passenger_ticket