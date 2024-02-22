from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
import json, logging
from ...tools.db_connector import GatewayConnector
import traceback
import copy
from dateutil.relativedelta import relativedelta
from ...tools import util
from ...tools import util,variables,ERR


_logger = logging.getLogger(__name__)


class TtProviderAirline(models.Model):
    _name = 'tt.provider.airline'
    _inherit = 'tt.history'
    _rec_name = 'pnr'
    _order = 'departure_date'
    _description = 'Provider Airline'

    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    pnr2 = fields.Char('PNR2', readonly=True, states={'draft': [('readonly', False)]})
    reference = fields.Char('Reference', default='', readonly=True, states={'draft': [('readonly', False)]}, help='PNR Reference if the airline provides another pnr reference number')
    provider_id = fields.Many2one('tt.provider','Provider', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft', readonly=True, states={'draft': [('readonly', False)]})
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', ondelete='cascade', readonly=True, states={'draft': [('readonly', False)]})
    sequence = fields.Integer('Sequence', readonly=True, states={'draft': [('readonly', False)]})
    balance_due = fields.Float('Balance Due', readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True, states={'draft': [('readonly', False)]})
    departure_date = fields.Char('Departure Date', readonly=True, states={'draft': [('readonly', False)]})
    return_date = fields.Char('Return Date', readonly=True, states={'draft': [('readonly', False)]})
    arrival_date = fields.Char('Arrival Date', readonly=True, states={'draft': [('readonly', False)]})
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)

    sid_issued = fields.Char('SID Issued', readonly=True, states={'draft': [('readonly', False)]})#signature generate sendiri
    sid_cancel = fields.Char('SID Cancel', readonly=True, states={'draft': [('readonly', False)]})#signature generate sendiri

    journey_ids = fields.One2many('tt.journey.airline', 'provider_booking_id', string='Journeys', readonly=True, states={'draft': [('readonly', False)]})
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_airline_booking_id', 'Cost Service Charges', readonly=True, states={'draft': [('readonly', False)]})

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    promotion_code = fields.Char(string='Promotion Code', readonly=True, states={'draft': [('readonly', False)]})


    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By', readonly=True, states={'draft': [('readonly', False)]})
    booked_date = fields.Datetime('Booking Date', readonly=True, states={'draft': [('readonly', False)]})
    issued_uid = fields.Many2one('res.users', 'Issued By', readonly=True, states={'draft': [('readonly', False)]})
    issued_date = fields.Datetime('Issued Date', readonly=True, states={'draft': [('readonly', False)]})
    hold_date = fields.Char('Price Guarantee Timelimit', readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Char('Expired Timelimit', readonly=True, states={'draft': [('readonly', False)]})
    cancel_uid = fields.Many2one('res.users', 'Cancel By', readonly=True, states={'draft': [('readonly', False)]})
    cancel_date = fields.Datetime('Cancel Date', readonly=True, states={'draft': [('readonly', False)]})
    #
    refund_uid = fields.Many2one('res.users', 'Refund By', readonly=True, states={'draft': [('readonly', False)]})
    refund_date = fields.Datetime('Refund Date', readonly=True, states={'draft': [('readonly', False)]})

    ticket_ids = fields.One2many('tt.ticket.airline', 'provider_id', 'Ticket Number', readonly=True, states={'draft': [('readonly', False)]})
    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    error_history_ids = fields.One2many('tt.reservation.err.history','res_id','Error History', domain=[('res_model','=','tt.provider.airline')], readonly=True, states={'draft': [('readonly', False)]})
    # , domain = [('res_model', '=', 'tt.provider.airline')]

    # April 23, 2020 - SAM
    penalty_amount = fields.Float('Penalty Amount', default=0, readonly=True, states={'draft': [('readonly', False)]})
    reschedule_uid = fields.Many2one('res.users', 'Rescheduled By', readonly=True, states={'draft': [('readonly', False)]})
    reschedule_date = fields.Datetime('Rescheduled Date', readonly=True, states={'draft': [('readonly', False)]})
    total_price = fields.Float('Total Price', default=0, readonly=True, states={'draft': [('readonly', False)]}, help='Issued Total Price (For reconcile)')
    total_price_cost = fields.Float('Total Price (Cost)', default=0, readonly=True, states={'draft': [('readonly', False)]})
    penalty_currency = fields.Char('Penalty Currency', default='', readonly=True, states={'draft': [('readonly', False)]})
    # END

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled', readonly=True, states={'draft': [('readonly', False)]})
    reconcile_time = fields.Datetime('Reconcile Time', readonly=True, states={'draft': [('readonly', False)]})
    ##
    is_hold_date_sync = fields.Boolean('Hold Date Sync', readonly=True, default=True)

    rule_ids = fields.One2many('tt.provider.airline.rule', 'provider_booking_id', string='Rules')

    # August 24, 2021 - SAM
    pricing_provider_line_ids = fields.One2many('tt.provider.airline.pricing.provider.line', 'provider_id', 'Pricing Provider Lines')
    pricing_agent_ids = fields.One2many('tt.provider.airline.pricing.agent', 'provider_id', 'Pricing Agents')
    # END

    # September 16, 2021 - SAM
    is_advance_purchase = fields.Boolean('Advance Purchase', readonly=True, default=False)
    # END

    # January 10, 2022 - SAM
    pricing_ids = fields.One2many('tt.provider.airline.pricing', 'provider_id', 'Pricing')
    # END

    # July 12, 2023 - SAM
    pnr_references = fields.Char('PNR References', default='')
    duplicates = fields.Char('Duplicates', default='')
    # END

    # October 19, 2023 - SAM
    notes = fields.Text('Notes')
    # END

    ##button function
    def action_change_is_hold_date_sync(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 103')
        self.write({
            'is_hold_date_sync': not self.is_hold_date_sync
        })

    def action_set_to_issued_from_button(self, payment_data={}):
        if self.state == 'issued':
            raise UserError("Has been Issued.")
        self.write({
            'state': 'issued',
            'is_hold_date_sync': True,
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
        payment_res = self.booking_id.payment_reservation_api('airline',req,context)
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

    def action_sync_refund_status(self):
        req = {
            'user_id': self.cancel_uid.id,
            'pnr': self.pnr,
            'pnr2': self.pnr2,
            'provider': self.provider_id.code,
            'ho_id': self.booking_id.agent_id.ho_id.id
        }
        res = self.env['tt.airline.api.con'].send_sync_refund_status(req)
        if res['error_code'] != 0:
            return False
        if res['response']['status'] == 'CANCELLED':
            self.write({
                'state': 'cancel',
                'is_hold_date_sync': True,
                'cancel_date': datetime.now()
            })
            self.booking_id.check_provider_state({'co_uid': self.cancel_uid.id})

    def action_reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 104')
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

        try:
            data = {
                'code': 9901,
                'title': 'PROVIDER AIRLINE REVERSE LEDGER',
                'message': 'Provider Ledger reversed from button: %s (%s)\nUser: %s\n' % (self.booking_id.name, self.pnr, self.env.user.name)
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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 105')
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

    # May 13, 2020 - SAM
    def action_reverse_ledger(self):
        for rec in self.booking_id.ledger_ids:
            pnr_text = self.pnr if self.pnr else str(self.sequence)
            if rec.pnr == pnr_text and not rec.is_reversed:
                rec.reverse_ledger()

        for rec in self.cost_service_charge_ids:
            rec.is_ledger_created = False
    # END

    # May 11, 2020 - SAM
    def set_provider_detail_info(self, provider_data):
        values = {}
        # todo ini buat ngambil semua key data dari response yang dikirim
        provider_data_keys = [key for key in provider_data.keys()]
        res_model = self.booking_id._name
        res_id = self.booking_id.id
        for key in ['pnr', 'pnr2', 'reference', 'balance_due', 'balance_due_str', 'total_price', 'penalty_amount', 'penalty_currency', 'is_hold_date_sync', 'is_advance_purchase', 'notes']:
            # if not provider_data.get(key):
            # todo ini buat ngecek klo key nya ada baru di update value nya
            if key not in provider_data_keys:
                continue
            if key == 'total_price':
                values['total_price_cost'] = provider_data[key]
                if self.state == 'issued':
                    continue

            values[key] = provider_data[key]
            # todo ini buat update data info pnr di ledger sama service charges (sblm booking itu sequence isi nya)
            if key == 'pnr':
                pnr = provider_data[key]
                provider_sequence = str(self.sequence)
                for sc in self.cost_service_charge_ids:
                    # todo ini kalau misal ternyata infonya uda pnr di skip, kalau belum di update
                    if sc.description != provider_data[key] and len(sc.description) < 5: ## default pnr 6 digit kalau uda di isi tidak di update (kata ko sam kalau update bukan fungsi yg ini)
                        sc.write({'description': pnr})

                updating_ledger_sequence_to_pnr = False
                for ledger in self.booking_id.ledger_ids:
                    # todo ini kalau misal ternyata infonya uda pnr di skip, kalau belum di update
                    if ledger.pnr == provider_sequence and len(ledger.pnr) < 5: ## default pnr 6 digit kalau uda di isi tidak di update (kata ko sam kalau update bukan fungsi yg ini)
                        ledger.write({'pnr': pnr})
                        updating_ledger_sequence_to_pnr = True
                if updating_ledger_sequence_to_pnr:
                    queue_ledger_objs = self.env['tt.ledger.queue'].search([('res_model','=',res_model),
                                                                            ('res_id','=',res_id),
                                                                            ('is_reverse_ledger_queue','=',False)])
                    for ledger_queue_obj in queue_ledger_objs:
                        ledger_data = json.loads(ledger_queue_obj.ledger_values_data)
                        if ledger_data['pnr'] == provider_sequence and len (ledger_data['pnr']) < 5:
                            ledger_data['pnr'] = pnr
                            ledger_queue_obj.ledger_values_data = json.dumps(ledger_data)


        if provider_data.get('hold_date'):
            values['hold_date'] = datetime.strptime(provider_data['hold_date'], "%Y-%m-%d %H:%M:%S")

        if provider_data.get('expired_date'):
            values['expired_date'] = datetime.strptime(provider_data['expired_date'], "%Y-%m-%d %H:%M:%S")

        # July 12, 2023 - SAM
        if provider_data.get('pnr_references'):
            try:
                pnr_references = ';'.join(provider_data['pnr_references'])
                values['pnr_references'] = pnr_references
            except:
                pass

        if provider_data.get('duplicates'):
            try:
                duplicates = ';'.join(provider_data['duplicates'])
                values['duplicates'] = duplicates
            except:
                pass
        # END

        # June 4, 2020 - SAM
        # Menambahkan info warning dari bookingan
        if provider_data.get('messages'):
            messages = provider_data['messages']
            if not type(messages) != list:
                messages = [str(messages)]
            error_msg = ', '.join(messages)
            error_history_ids = [(0, 0, {
                'res_model': self._name,
                'res_id': self.id,
                'error_code': 0,
                'error_msg': error_msg
            })]
            values['error_history_ids'] = error_history_ids
        # END
        return values
    # END

    # April 24, 2020 - SAM
    def action_booked_api_airline(self, provider_data, api_context):
        for rec in self:
            values = {
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            }

            provider_values = rec.set_provider_detail_info(provider_data)
            if provider_values:
                values.update(provider_values)

            rec.write(values)

    # def action_booked_api_airline(self, api_context):
    #     for rec in self:
    #         rec.write({
    #             'state': 'booked',
    #             'booked_uid': api_context['co_uid'],
    #             'booked_date': fields.Datetime.now(),
    #         })

    def action_booked_pending_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'booked_pending',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })

    def action_void_pending_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'void_pending',
                'cancel_uid': api_context['co_uid'],
                'cancel_date': fields.Datetime.now(),
            })

    def action_void_api_airline(self, provider_data, api_context):
        for rec in self:
            values = {
                'state': 'void',
                'is_hold_date_sync': True,
                'cancel_uid': api_context['co_uid'],
                'cancel_date': fields.Datetime.now(),
            }
            provider_values = rec.set_provider_detail_info(provider_data)
            if provider_values:
                values.update(provider_values)
            rec.write(values)

    def action_issued_pending_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'issued_pending',
                'issued_uid': api_context['co_uid'],
                'issued_date': fields.Datetime.now(),
            })

    def action_refund_api_airline(self, provider_data, api_context):
        for rec in self:
            values = {
                'state': 'refund',
                'is_hold_date_sync': True,
                'refund_uid': api_context['co_uid'],
                'refund_date': fields.Datetime.now(),
            }
            provider_values = rec.set_provider_detail_info(provider_data)
            if provider_values:
                values.update(provider_values)
            rec.write(values)

    def action_rescheduled_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'rescheduled',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_reissue_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'reissue',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_rescheduled_pending_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'rescheduled_pending',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_halt_booked_api_airline(self, api_context,err_code=0,err_msg=''):
        for rec in self:
            data = {
                'state': 'halt_booked',
                'hold_date': datetime.now().replace(microsecond=0) + timedelta(minutes=10)
            }
            if err_code != 0:
                data.update({
                    'error_history_ids': [(0, 0, {
                        'res_model': self._name,
                        'res_id': self.id,
                        'error_code': err_code,
                        'error_msg': err_msg
                    })]
                })
            rec.write(data)

    def action_halt_issued_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'halt_issued',
                'hold_date': datetime.now().replace(microsecond=0) + timedelta(minutes=30)
            })

    def action_failed_void_api_airline(self,err_code,err_msg):
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

    def action_refund_failed_api_airline(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'refund_failed',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })

    def action_failed_rescheduled_api_airline(self,err_code,err_msg):
        for rec in self:
            rec.write({
                'state': 'rescheduled_failed',
                'error_history_ids': [(0,0,{
                    'res_model': self._name,
                    'res_id': self.id,
                    'error_code': err_code,
                    'error_msg': err_msg
                })]
            })
    # END

    # May 20, 2020 - SAM
    # def action_issued_api_airline(self,context):
    def action_issued_api_airline(self, provider_data, context):
        for rec in self:
            values = {
                'state': 'issued',
                'is_hold_date_sync': True,
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
            }
            if not rec.booked_date:
                values.update({
                    'booked_date': values['issued_date'],
                    'booked_uid': values['issued_uid'],
                })
            provider_values = rec.set_provider_detail_info(provider_data)
            if provider_values:
                values.update(provider_values)
            rec.write(values)
    # END

    def action_cancel_api_airline(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'is_hold_date_sync': True,
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_refund_pending_api_airline(self,context):
        for rec in self:
            rec.write({
                'state': 'refund_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_cancel_pending_api_airline(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_failed_booked_api_airline(self,err_code,err_msg):
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

    def action_failed_issued_api_airline(self,err_code,err_msg):
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

    def action_expired(self):
        self.state = 'cancel2'

    def action_cancel(self):
        # self.cancel_date = fields.Datetime.now()
        # self.cancel_uid = self.env.user.id
        # self.state = 'cancel'
        self.write({
            'state': 'cancel',
            'cancel_date': fields.Datetime.now(),
            'cancel_uid': self.env.user.id,
            'is_hold_date_sync': True
        })

    def action_refund(self, check_provider_state=False):
        # self.state = 'refund'
        self.write({
            'state': 'refund',
            'is_hold_date_sync': True
        })
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_ticket_api(self,passengers,pnr="", departure_date=''):
        ticket_list = []
        ticket_not_found = []

        #################
        for passenger in self.booking_id.passenger_ids:
            passenger.is_ticketed = False
        #################

        for psg in passengers:
            psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() ==
                                                                ('%s%s' % (psg.get('first_name', ''),
                                                                           psg.get('last_name', ''))).lower().replace(' ',''))

            if not psg_obj:
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower()*2 ==
                                                                           ('%s%s' % (psg.get('first_name', ''),
                                                                                      psg.get('last_name',
                                                                                              ''))).lower().replace(' ',''))

            # September 29, 2021 - SAM
            # Menambahkan mekanisme match data tiket
            # Ada vendor yang memotong pada first_name
            if not psg_obj:
                psg_name = '%s%s' % (psg.get('last_name', '').lower().replace(' ', ''), psg.get('first_name', '').lower().replace(' ', ''))
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: psg_name in '%s%s' % (x.last_name.lower().replace(' ', '') if x.last_name else '', x.first_name.lower().replace(' ', '') if x.first_name else ''))

            if not psg_obj:
                psg_name = '%s%s' % (psg.get('last_name', '').lower().replace(' ', ''), psg.get('first_name', '').lower().replace(' ', ''))
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: psg_name in '%s%s' % (x.first_name.lower().replace(' ', '') if x.first_name else '', x.first_name.lower().replace(' ', '') if x.first_name else ''))
            # END

            if psg_obj:
                _logger.info(json.dumps(psg_obj.ids))
                if len(psg_obj.ids) > 1:
                    for psg_o in psg_obj:
                        if not psg_o.is_ticketed:
                            psg_obj = psg_o
                            break

                _logger.info(str(psg_obj))
                ticket_number_list = ''
                try:
                    if psg.get('ticket_number_list'):
                        merge_tickets = ';'.join(psg['ticket_number_list'])
                        ticket_number_list = merge_tickets
                except:
                    pass
                ticket_vals = {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': psg.get('ticket_number'),
                    'passenger_id': psg_obj.id,
                    'ff_number': psg.get('ff_number'),
                    'ff_code': psg.get('ff_code'),
                    'title': psg.get('title'),
                    'first_name': psg.get('first_name'),
                    'last_name': psg.get('last_name'),
                    'birth_date': psg.get('birth_date'),
                    'identity_type': psg.get('identity_type'),
                    'identity_number': psg.get('identity_number'),
                    'identity_expdate': psg.get('identity_expdate'),
                    'identity_country_of_issued_code': psg.get('identity_country_of_issued_code'),
                    'ticket_number_list': ticket_number_list,
                    'riz_text': psg.get('riz_text'),
                }
                ticket_list.append((0, 0, ticket_vals))
                psg_obj.is_ticketed = True
                psg_obj.create_ssr(psg['fees'],pnr,self.id)
            else:
                _logger.info("psg not found :" + json.dumps(psg))
                _logger.info("psg info: %s " % (
                    ','.join([rec.name.replace(' ', '').lower() for rec in self.booking_id.passenger_ids])
                ))
                ticket_not_found.append(psg)

        psg_with_no_ticket = self.booking_id.passenger_ids.filtered(lambda x: x.is_ticketed == False)
        for idx, psg in enumerate(ticket_not_found):
            ticket_number_list = ''
            try:
                if psg.get('ticket_number_list'):
                    merge_tickets = ';'.join(psg['ticket_number_list'])
                    ticket_number_list = merge_tickets
            except:
                pass
            ticket_vals = {
                'pax_type': psg.get('pax_type'),
                'ticket_number': psg.get('ticket_number'),
                'ff_number': psg.get('ff_number'),
                'ff_code': psg.get('ff_code'),
                'title': psg.get('title'),
                'first_name': psg.get('first_name'),
                'last_name': psg.get('last_name'),
                'birth_date': psg.get('birth_date'),
                'identity_type': psg.get('identity_type'),
                'identity_number': psg.get('identity_number'),
                'identity_expdate': psg.get('identity_expdate'),
                'identity_country_of_issued_code': psg.get('identity_country_of_issued_code'),
                'ticket_number_list': ticket_number_list,
            }
            if idx >= len(psg_with_no_ticket):
                ticket_list.append((0, 0, ticket_vals))
            else:
                ticket_vals.update({
                    'passenger_id': psg_with_no_ticket[idx].id
                })
                ticket_list.append((0, 0, ticket_vals))
                psg_with_no_ticket[idx].is_ticketed = True
                psg_with_no_ticket[idx].create_ssr(psg['fees'],pnr,self.id)

        # March 28, 2022 - SAM
        # Antisipasi struktur gateway yang miss
        if psg_with_no_ticket:
            date_now = datetime.now()
            if departure_date:
                date_now = datetime.strptime(departure_date, '%Y-%m-%d %H:%M:%S')

            for psg_obj in psg_with_no_ticket:
                if psg_obj.is_ticketed:
                    continue

                pax_type = 'ADT'
                if psg_obj.birth_date:
                    difference = relativedelta(date_now, psg_obj.birth_date).years
                    if difference < 2:
                        pax_type = 'INF'
                    elif difference < 12:
                        pax_type = 'CHD'

                ticket_list.append((0, 0, {
                    'pax_type': pax_type,
                    'ticket_number': '',
                    'passenger_id': psg_obj.id
                }))
                psg_obj.is_ticketed = True
        # END

        self.write({
            'ticket_ids': ticket_list
        })

    def update_ticket_api(self, passengers):
        # July 10, 2023 - SAM
        # Init data pax dari backend (reservasi)
        backend_pax_repo = []
        backend_pax_obj_repo = {}
        if self.booking_id:
            for rec in self.booking_id.passenger_ids:
                first_name = ''.join(rec.first_name.split()).lower() if rec.first_name else ''
                last_name = ''.join(rec.last_name.split()).lower() if rec.last_name else ''
                title = ''.join(rec.title.split()).lower() if rec.title else ''
                key_1 = '%s%s%s' % (last_name, first_name, title)
                key_2 = '%s%s%s' % (first_name, first_name, title)
                key_3 = '%s%s' % (last_name, first_name)
                key_4 = '%s%s' % (first_name, first_name)
                vals = {
                    'passenger_id': rec.id,
                    'key_1': key_1,
                    'key_2': key_2,
                    'key_3': key_3,
                    'key_4': key_4,
                    'first_name': rec.first_name if rec.first_name else '',
                    'last_name': rec.last_name if rec.last_name else '',
                    'has_ticket': False,
                }
                backend_pax_repo.append(vals)
                backend_pax_obj_repo[str(rec.id)] = rec

        # Init data pax dari provider tickets
        ticket_repo = []
        ticket_obj_repo = {}
        for rec in self.ticket_ids:
            vals = {
                'ticket_id': rec.id,
                'passenger_id': '',
                'key_1': '',
                'key_2': '',
                'key_3': '',
                'key_4': '',
                'title': '',
                'first_name': '',
                'last_name': '',
                'is_sync': False,
            }
            if rec.first_name or rec.last_name:
                first_name = ''.join(rec.first_name.split()).lower() if rec.first_name else ''
                last_name = ''.join(rec.last_name.split()).lower() if rec.last_name else ''
                title = ''.join(rec.title.split()).lower() if rec.title else ''
                key_1 = '%s%s%s' % (last_name, first_name, title)
                key_2 = '%s%s%s' % (first_name, first_name, title)
                key_3 = '%s%s' % (last_name, first_name)
                key_4 = '%s%s' % (first_name, first_name)
                vals.update({
                    'title': rec.title if rec.title else '',
                    'key_1': key_1,
                    'key_2': key_2,
                    'key_3': key_3,
                    'key_4': key_4,
                    'first_name': rec.first_name if rec.first_name else '',
                    'last_name': rec.last_name if rec.last_name else '',
                })
                if rec.passenger_id:
                    vals.update({'passenger_id': rec.passenger_id.id})
            elif rec.passenger_id:
                is_found = False
                for psg in backend_pax_repo:
                    if psg['passenger_id'] == rec.passenger_id:
                        is_found = True
                        vals.update(copy.deepcopy(psg))
                        if 'has_ticket' in vals:
                            vals.pop('has_ticket')
                        break
                if not is_found:
                    psg_obj = rec.passenger_id
                    first_name = ''.join(psg_obj.first_name.split()).lower() if psg_obj.first_name else ''
                    last_name = ''.join(psg_obj.last_name.split()).lower() if psg_obj.last_name else ''
                    title = ''.join(psg_obj.title.split()).lower() if psg_obj.title else ''
                    key_1 = '%s%s%s' % (last_name, first_name, title)
                    key_2 = '%s%s%s' % (first_name, first_name, title)
                    key_3 = '%s%s' % (last_name, first_name)
                    key_4 = '%s%s' % (first_name, first_name)
                    vals.update({
                        'key_1': key_1,
                        'key_2': key_2,
                        'key_3': key_3,
                        'key_4': key_4,
                        'title': psg_obj.title if psg_obj.title else '',
                        'first_name': psg_obj.first_name if psg_obj.first_name else '',
                        'last_name': psg_obj.last_name if psg_obj.last_name else '',
                        'passenger_id': psg_obj.id,
                    })
            ticket_repo.append(vals)
            ticket_obj_repo[str(rec.id)] = rec

        # Check dan update data
        ticket_ids = []
        new_ticket_list = []
        for rec in passengers:
            # Setup data
            ticket_vals = {
                'pax_type': rec.get('pax_type', ''),
                'ticket_number': rec.get('ticket_number', ''),
                'ff_number': rec.get('ff_number', ''),
                'ff_code': rec.get('ff_code', ''),
                'title': rec.get('title', ''),
                'first_name': rec.get('first_name', ''),
                'last_name': rec.get('last_name', ''),
                'birth_date': rec.get('birth_date', ''),
                'identity_type': '',
                'identity_number': '',
                'identity_expdate': '',
                'identity_country_of_issued_code': '',
                'ticket_number_list': '',
                'riz_text': rec.get('riz_text', ''),
            }
            if rec.get('identity'):
                ticket_vals.update({
                    'identity_type': rec['identity'].get('identity_type', ''),
                    'identity_number': rec['identity'].get('identity_number', ''),
                    'identity_expdate': rec['identity'].get('identity_expdate', ''),
                    'identity_country_of_issued_code': rec['identity'].get('identity_country_of_issued_code', ''),
                })
            if rec.get('ticket_number_list'):
                try:
                    ticket_number_list = ';'.join(rec['ticket_number_list'])
                    if ticket_number_list:
                        ticket_vals['ticket_number_list'] = ticket_number_list
                except:
                    pass

            # Setup key
            first_name = ''.join(rec['first_name'].split()).lower() if rec.get('first_name') else ''
            last_name = ''.join(rec['last_name'].split()).lower() if rec.get('last_name') else ''
            title = ''.join(rec['title'].split()).lower() if rec.get('title') else ''
            key_1 = '%s%s%s' % (last_name, first_name, title)
            key_2 = '%s%s%s' % (first_name, first_name, title)
            key_3 = '%s%s' % (last_name, first_name)
            key_4 = '%s%s' % (first_name, first_name)
            key_type = '1'
            if not first_name or not last_name:
                key_type = '2'
            elif first_name == last_name:
                key_type = '2'

            # Search if data exist, update
            is_ticket_found = False
            for tkt in ticket_repo:
                if tkt['is_sync']:
                    continue
                # if key_1 in tkt['key_1'] or key_2 in tkt['key_2']:
                if rec.get('title'):
                    if (key_type == '1' and key_1 == tkt['key_1']) or (key_type == '2' and key_2 == tkt['key_2']):
                        is_ticket_found = True
                        tkt['is_sync'] = True
                        ticket_ids.append((1, tkt['ticket_id'], ticket_vals))
                        if tkt['passenger_id']:
                            for psg in backend_pax_repo:
                                if psg['passenger_id'] == tkt['passenger_id']:
                                    psg['has_ticket'] = True
                                    break
                            if str(tkt['passenger_id']) in backend_pax_obj_repo:
                                backend_pax_obj_repo[str(tkt['passenger_id'])].is_ticketed = True
                        else:
                            for psg in backend_pax_repo:
                                if key_1 == psg['key_1'] or key_2 == psg['key_2']:
                                    psg['has_ticket'] = True
                                    passenger_id = psg['passenger_id']
                                    if str(passenger_id) in backend_pax_obj_repo:
                                        backend_pax_obj_repo[str(passenger_id)].is_ticketed = True
                                    ticket_vals.update({
                                        'passenger_id': passenger_id
                                    })
                                    break
                        break
                else:
                    if (key_type == '1' and key_3 == tkt['key_3']) or (key_type == '2' and key_4 == tkt['key_4']):
                        is_ticket_found = True
                        tkt['is_sync'] = True
                        if 'title' in ticket_vals:
                            ticket_vals.pop('title')
                        ticket_ids.append((1, tkt['ticket_id'], ticket_vals))
                        if tkt['passenger_id']:
                            for psg in backend_pax_repo:
                                if psg['passenger_id'] == tkt['passenger_id']:
                                    psg['has_ticket'] = True
                                    break
                            if str(tkt['passenger_id']) in backend_pax_obj_repo:
                                backend_pax_obj_repo[str(tkt['passenger_id'])].is_ticketed = True
                        else:
                            for psg in backend_pax_repo:
                                if key_3 == psg['key_3'] or key_4 == psg['key_4']:
                                    psg['has_ticket'] = True
                                    passenger_id = psg['passenger_id']
                                    if str(passenger_id) in backend_pax_obj_repo:
                                        backend_pax_obj_repo[str(passenger_id)].is_ticketed = True
                                    ticket_vals.update({
                                        'passenger_id': passenger_id
                                    })
                                    break
                        break
            # if not exist, tampung dulu
            if not is_ticket_found:
                new_ticket_list.append(ticket_vals)

        if new_ticket_list:
            # Hitung jumlah pax backend yang belum punya tiket
            new_ticket_count = len(new_ticket_list)
            no_ticket_backend_pax_count = 0
            no_ticket_backend_pax_list = []
            for rec in backend_pax_repo:
                if not rec['has_ticket']:
                    no_ticket_backend_pax_count += 1
                    no_ticket_backend_pax_list.append(rec)

            # Kalau sama sama 1, langsung update data backend
            if new_ticket_count == 1 and no_ticket_backend_pax_count == 1:
                tkt_vals = new_ticket_list[0]
                psg_vals = no_ticket_backend_pax_list[0]
                passenger_id = psg_vals['passenger_id']
                tkt_vals.update({
                    'passenger_id': passenger_id
                })
                if str(passenger_id) in backend_pax_obj_repo:
                    name_list = []
                    if tkt_vals['first_name']:
                        name_list.append(tkt_vals['first_name'])
                    if tkt_vals['last_name']:
                        name_list.append(tkt_vals['last_name'])
                    name = ' '.join(name_list)
                    write_vals = {
                        'name': name,
                        'first_name': tkt_vals['first_name'],
                        'last_name': tkt_vals['last_name'],
                    }
                    if tkt_vals.get('title'):
                        write_vals['title'] = tkt_vals['title']
                    backend_pax_obj_repo[str(passenger_id)].write(write_vals)
                    if backend_pax_obj_repo[str(passenger_id)].customer_id:
                        backend_pax_obj_repo[str(passenger_id)].customer_id.write({
                            'first_name': tkt_vals['first_name'],
                            'last_name': tkt_vals['last_name'],
                        })
            for tkt in new_ticket_list:
                ticket_ids.append((0, 0, tkt))

        # Hapus ticket yang tidak tersync
        for rec in ticket_repo:
            if not rec['is_sync']:
                ticket_ids.append((2, rec['ticket_id']))
        self.write({
            'ticket_ids': ticket_ids
        })
        # END

    def update_ticket_api_backup_20230710(self,passengers):##isi ticket number
        ticket_not_found = []
        # September 29, 2021 - SAM
        # Update mekanisme kriteria match tiket.
        # Mekanisme match digunakan ilike, karena pada vendor nama bisa terpotong
        match_ticket_list = []
        for psg in passengers:
            psg_name_1 = '%s%s' % (psg.get('first_name', '').lower().replace(' ', ''), psg.get('last_name', '').lower().replace(' ', ''))
            psg_name_2 = '%s%s' % (psg.get('last_name', '').lower().replace(' ', ''), psg.get('first_name', '').lower().replace(' ', ''))
            psg_ticket_number = psg.get('ticket_number', '')
            has_ticket_number = True if psg_ticket_number else False

            ticket_found = False
            for ticket in self.ticket_ids:
                if ticket.id in match_ticket_list:
                    continue

                # ticket_passenger_name = ticket.passenger_id and ticket.passenger_id.name or ''
                # psg_name = ticket_passenger_name.replace(' ','').lower()
                # if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ','').lower() in [psg_name, psg_name*2] and not ticket.ticket_number or (psg.get('ticket_number') and ticket.ticket_number == psg.get('ticket_number')):
                if ticket.passenger_id:
                    ticket_first_name = ticket.passenger_id.first_name.lower().replace(' ', '') if ticket.passenger_id.first_name else ''
                    ticket_last_name = ticket.passenger_id.last_name.lower().replace(' ', '') if ticket.passenger_id.last_name else ''
                    ticket_name_1 = '%s%s' % (ticket_first_name, ticket_last_name)
                    ticket_name_2 = '%s%s' % (ticket_last_name, ticket_first_name)
                    ticket_name_3 = '%s%s' % (ticket_first_name, ticket_first_name)
                    ticket_number = ticket.ticket_number if ticket.ticket_number else ''

                    is_match = False
                    if ticket_number:
                        if has_ticket_number and psg_ticket_number == ticket_number:
                            is_match = True
                    else:
                        if (psg_name_1 in ticket_name_1) or (psg_name_1 in ticket_name_3) or (psg_name_2 in ticket_name_2) or (psg_name_2 in ticket_name_3):
                            is_match = True
                    if is_match:
                        match_ticket_list.append(ticket.id)
                        ticket_values = {
                            'ticket_number': psg.get('ticket_number', ''),
                            'ff_number': psg.get('ff_number', ''),
                            'ff_code': psg.get('ff_code', ''),
                        }
                        if not ticket.pax_type or (psg.get('pax_type') and psg['pax_type'] != ticket.pax_type):
                            ticket_values.update({
                                'pax_type': psg['pax_type']
                            })
                        # if ticket_values['ff_code']:
                        #     loyalty_id = self.env['tt.loyalty.program'].sudo().get_id(ticket_values['ff_code'])
                        #     if loyalty_id:
                        #         ticket_values['loyalty_program_id'] = loyalty_id
                        ticket.write(ticket_values)
                        ticket_found = True
                        ticket.passenger_id.is_ticketed = True
                        break
            if not ticket_found:
                ticket_not_found.append(psg)
        # END

        for psg in ticket_not_found:
            # April 21, 2020 - SAM
            # self.write({
            #     'ticket_ids': [(0,0,{
            #         'ticket_number': psg.get('ticket_number'),
            #         'pax_type': psg.get('pax_type'),
            #     })]
            # })
            ticket_values = {
                'ticket_number': psg.get('ticket_number'),
                'ff_number': psg.get('ff_number', ''),
                'pax_type': psg.get('pax_type'),
            }
            if psg.get('passenger_id'):
                ticket_values['passenger_id'] = psg['passenger_id']
            # if ticket_values['ff_code']:
            #     loyalty_id = self.env['tt.loyalty.program'].sudo().get_id(ticket_values['ff_code'])
            #     if loyalty_id:
            #         ticket_values['loyalty_program_id'] = loyalty_id
            self.write({
                'ticket_ids': [(0, 0, ticket_values)]
            })
            # END

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            # update 19 Feb 2020 maximum per pax sesuai dengan pax_count dari service charge
            # scs['pax_count'] = 0
            # April 28, 2020 - SAM
            currency_id = currency_obj.get_id(scs.get('currency'),default_param_idr=True)
            foreign_currency_id = currency_obj.get_id(scs.get('foreign_currency'),default_param_idr=True)
            scs_pax_count = 0
            total = 0
            # scs['passenger_airline_ids'] = []
            # scs['total'] = 0
            # scs['currency_id'] = currency_obj.get_id(scs.get('currency'),default_param_idr=True)
            # scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'),default_param_idr=True)
            # scs['provider_airline_booking_id'] = self.id
            passenger_airline_ids = []
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    # scs['passenger_airline_ids'].append(psg.passenger_id.id)
                    passenger_airline_ids.append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    # scs['total'] += scs['amount']
                    total += scs['amount']
            scs.update({
                'passenger_airline_ids': [(6, 0, passenger_airline_ids)],
                'total': total,
                'currency_id': currency_id,
                'foreign_currency_id': foreign_currency_id,
                'provider_airline_booking_id': self.id,
                'description': self.pnr and self.pnr or str(self.sequence),
                'ho_id': self.booking_id.ho_id.id if self.booking_id and self.booking_id.ho_id else ''
            })
            scs.pop('currency')
            scs.pop('foreign_currency')
            # scs['passenger_airline_ids'] = [(6,0,scs['passenger_airline_ids'])]
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
        # May 13, 2020 - SAM
        # for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
        for rec in self.cost_service_charge_ids:
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        # END
        return ledger_created

    # May 14, 2020 - SAM
    def delete_passenger_fees(self):
        for psg in self.booking_id.passenger_ids:
            # unlink fees punya-nya current provider
            for fee in psg.fee_ids.filtered(lambda fees: fees.provider_id and fees.provider_id.id == self.id):
                fee.unlink()

    def delete_passenger_tickets(self):
        # June 30, 2021 - SAM
        # unlink dengan metode update One2many
        # for ticket in self.ticket_ids:
        #     ticket.unlink()
        self.write({
            'ticket_ids': [(5, 0, 0)]
        })
    # END

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

    def action_create_ledger(self,issued_uid,pay_method=None, use_point=False, payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self,issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)
        # else:
        #     raise UserError("Cannot create ledger, ledger has been created before.")

    def to_dict(self):
        journey_list = []
        for rec in self.journey_ids:
            journey_list.append(rec.to_dict())
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())

        service_charges = []
        for rec in self.cost_service_charge_ids:
            if rec.charge_type == 'RAC' and not rec.charge_code == 'rac':
                continue
            service_charges.append(rec.to_dict())

        rules = []
        for rec in self.rule_ids:
            rules.append(rec.to_dict())

        # July 12, 2023 - SAM
        pnr_references = []
        try:
            if self.pnr_references:
                temp = [rec.strip() for rec in self.pnr_references.split(';')]
                pnr_references = temp
        except:
            pass

        duplicates = []
        try:
            if self.duplicates:
                temp = [rec.strip() for rec in self.duplicates.split(';')]
                duplicates = temp
        except:
            pass
        # END

        # September 12, 2023 - SAM
        pricing_data = {}
        if self.pricing_ids:
            pricing_data = self.pricing_ids[0].to_dict()
        # END

        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'agent_id': self.booking_id.agent_id.id if self.booking_id and self.booking_id.agent_id else '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'balance_due': self.balance_due,
            'origin': self.origin_id.code,
            'origin_display_name': self.origin_id.name,
            'destination': self.destination_id.code,
            'destination_display_name': self.destination_id.name,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
            'error_msg': self.error_history_ids and self.error_history_ids[-1].error_msg or '',
            # 'service_charges': service_charges,
            # April 29, 2020 - SAM
            'reference': self.reference,
            'total_price': self.total_price,
            'total_price_cost': self.total_price_cost if self.total_price_cost else self.total_price,
            'penalty_amount': self.penalty_amount,
            'penalty_currency': self.penalty_currency and self.penalty_currency or '',
            'is_advance_purchase': self.is_advance_purchase,
            'is_force_issued': self.booking_id.is_force_issued,
            'is_halt_process': self.booking_id.is_halt_process,
            # END
            # June 28, 2021 - SAM
            'rules': rules,
            # END
            # July 12, 2023 - SAM
            'pnr_references': pnr_references,
            'duplicates': duplicates,
            # END
            # September 12, 2023 - SAM
            'pricing_data': pricing_data,
            # END
        }
        return res

    def get_carrier_name(self):
        carrier_names = set([])
        for journey in self.journey_ids:
            for segment in journey.segment_ids:
                if segment.carrier_id:
                    carrier_names.add(segment.carrier_id.name)
        return carrier_names

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

    # June 2, 2021 - SAM
    def action_reprice_provider(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 106')
        if not self.provider_id:
            raise Exception('Provider is not set')

        user_id = self.booking_id.user_id

        co_user_info = self.env['tt.agent'].sudo().get_agent_level(user_id.agent_id.id)
        context = {
            "co_uid": user_id.id,
            "co_user_name": user_id.name,
            "co_user_login": user_id.login,
            "co_agent_id": user_id.agent_id.id,
            "co_agent_name": user_id.agent_id.name,
            "co_agent_type_id": user_id.agent_id.agent_type_id.id,
            "co_agent_type_name": user_id.agent_id.agent_type_id.name,
            "co_agent_type_code": user_id.agent_id.agent_type_id.code,
            "co_user_info": co_user_info,
            "co_ho_id": user_id.agent_id.ho_id.id
        }

        req = {
            "provider": self.provider_id.code,
            "pnr": self.pnr,
            "pnr2": self.pnr2,
            "reference": self.reference,
            "context": context,
        }
        res = self.env['tt.airline.api.con'].send_reprice_booking_vendor(req)
        _logger.info('Action Reprice Provider, %s-%s, %s' % (self.pnr, self.provider_id.code, json.dumps(res)))

        try:
            if res['error_code'] != 0:
                order_number = self.booking_id.name if self.booking_id else ''
                msg = [
                    'Reprice Provider - ERROR',
                    '',
                    'Order Number: %s' % order_number,
                    'PNR: %s' % self.pnr,
                    'Error: %s' % res['error_msg'],
                ]
                data = {
                    'code': 9903,
                    'message': '\n'.join(msg),
                    'provider': self.provider_id.code,
                }
                context = {
                    "co_ho_id": self.booking_id.agent_id.ho_id.id
                }
                GatewayConnector().telegram_notif_api(data, context)
                return False

            order_number = self.booking_id.name if self.booking_id else ''
            msg = [
                'Reprice Provider - SUCCESS',
                '',
                'Order Number: %s' % order_number,
                'PNR: %s' % self.pnr,
                'Original Total Price: %s' % self.total_price,
                'New Total Price: %s' % res['response']['total_price'],
            ]
            data = {
                'code': 9901,
                'message': '\n'.join(msg),
                'provider': self.provider_id.code,
            }
            context = {
                "co_ho_id": self.booking_id.agent_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except:
            _logger.error('Action reprice provider, error notif telegram, %s, %s' % (self.pnr, traceback.format_exc()))

        return True
    # END

    # March 28, 2022 - SAM
    def action_void_provider(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 107')
        if not self.provider_id:
            raise Exception('Provider is not set')

        user_id = self.booking_id.user_id

        co_user_info = self.env['tt.agent'].sudo().get_agent_level(user_id.agent_id.id)
        context = {
            "co_uid": user_id.id,
            "co_user_name": user_id.name,
            "co_user_login": user_id.login,
            "co_agent_id": user_id.agent_id.id,
            "co_agent_name": user_id.agent_id.name,
            "co_agent_type_id": user_id.agent_id.agent_type_id.id,
            "co_agent_type_name": user_id.agent_id.agent_type_id.name,
            "co_agent_type_code": user_id.agent_id.agent_type_id.code,
            "co_user_info": co_user_info,
            "co_ho_id": user_id.agent_id.ho_id.id
        }

        req = {
            "provider": self.provider_id.code,
            "pnr": self.pnr,
            "pnr2": self.pnr2,
            "reference": self.reference,
            "context": context
        }
        passengers = self.booking_id.passenger_ids.to_dict()
        req.update({
            'booking_data': {
                'passengers': passengers
            }
        })
        res = self.env['tt.airline.api.con'].send_void_booking_vendor(req)
        _logger.info('Action Void Provider, %s-%s, %s' % (self.pnr, self.provider_id.code, json.dumps(res)))

        try:
            if res['error_code'] != 0:
                order_number = self.booking_id.name if self.booking_id else ''
                msg = [
                    'Void Provider - ERROR',
                    '',
                    'Order Number: %s' % order_number,
                    'PNR: %s' % self.pnr,
                    'Error: %s' % res['error_msg'],
                ]
                data = {
                    'code': 9903,
                    'message': '\n'.join(msg),
                    'provider': self.provider_id.code,
                }
                context = {
                    "co_ho_id": self.booking_id.agent_id.ho_id.id
                }
                GatewayConnector().telegram_notif_api(data, context)
                raise UserError('Error void, %s' % res['error_msg'])

            order_number = self.booking_id.name if self.booking_id else ''
            msg = [
                'Void Provider - SUCCESS',
                '',
                'Order Number: %s' % order_number,
                'PNR: %s' % self.pnr,
            ]
            data = {
                'code': 9901,
                'message': '\n'.join(msg),
                'provider': self.provider_id.code,
            }
            context = {
                "co_ho_id": self.booking_id.agent_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except UserError as e:
            raise UserError(str(e))
        except:
            _logger.error('Action void provider, error notif telegram, %s, %s' % (self.pnr, traceback.format_exc()))

        try:
            response = res['response']
            if response['status'] in ['VOID', 'REFUND']:
                self.write({
                    'cancel_uid': self.env.uid,
                    'cancel_date': datetime.now(),
                    'state': 'void',
                })

                for rec in self.booking_id.ledger_ids:
                    if rec.pnr in [self.pnr, str(self.sequence)] and not rec.is_reversed:
                        rec.reverse_ledger()

                for rec in self.cost_service_charge_ids:
                    rec.is_ledger_created = False

            ctx = {
                'co_uid': self.env.uid
            }
            self.booking_id.check_provider_state(ctx)
        except:
            _logger.error('Action void provider, error update provider state, %s, %s' % (self.pnr, traceback.format_exc()))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    # END

    def update_void_provider_booking_api(self, data, context):
        response = data['response']
        provider_objs = self.search([("pnr",'=', response['pnr']), ("pnr2",'=',response['pnr2']), ("reference",'=', response['reference'])])
        for provider_obj in provider_objs:
            try:
                if response['status'] in ['VOID', 'REFUND']:
                    provider_obj.write({
                        'cancel_uid': context['co_uid'],
                        'cancel_date': datetime.now(),
                        'state': 'void',
                    })

                    for rec in provider_obj.booking_id.ledger_ids:
                        if rec.pnr in [self.pnr, str(self.sequence)] and not rec.is_reversed:
                            rec.reverse_ledger()

                    for rec in provider_obj.cost_service_charge_ids:
                        rec.is_ledger_created = False

                ctx = {
                    'co_uid': context['co_uid']
                }
                provider_obj.booking_id.check_provider_state(ctx)
            except Exception as e:
                _logger.error('Action void provider, error update provider state, %s, %s' % (provider_obj.pnr, traceback.format_exc()))
                return ERR.get_error(500)
        return ERR.get_no_error()

    # March 08, 2023 - SAM
    def action_check_segment_provider(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 107')
        if not self.provider_id:
            raise Exception('Provider is not set')

        user_id = self.booking_id.user_id

        co_user_info = self.env['tt.agent'].sudo().get_agent_level(user_id.agent_id.id)
        context = {
            "co_uid": user_id.id,
            "co_user_name": user_id.name,
            "co_user_login": user_id.login,
            "co_agent_id": user_id.agent_id.id,
            "co_agent_name": user_id.agent_id.name,
            "co_agent_type_id": user_id.agent_id.agent_type_id.id,
            "co_agent_type_name": user_id.agent_id.agent_type_id.name,
            "co_agent_type_code": user_id.agent_id.agent_type_id.code,
            "co_user_info": co_user_info,
            "co_ho_id": user_id.agent_id.ho_id.id
        }

        req = {
            "provider": self.provider_id.code,
            "pnr": self.pnr,
            "pnr2": self.pnr2,
            "reference": self.reference,
            "context": context,
        }
        res = self.env['tt.airline.api.con'].send_check_segment_vendor(req)
        _logger.info('Action Check Segment Provider, %s-%s, %s' % (self.pnr, self.provider_id.code, json.dumps(res)))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    # END

    def update_pricing_details(self, fare_data):
        try:
            pricing_provider_line_ids = []
            for rec in self.pricing_provider_line_ids:
                pricing_provider_line_ids.append((2, rec.id))
            if 'pricing_provider_list' in fare_data:
                for pp in fare_data['pricing_provider_list']:
                    pricing_provider_line_ids.append((0, 0, pp))

            pricing_agent_ids = []
            for rec in self.pricing_agent_ids:
                pricing_agent_ids.append((2, rec.id))
            if 'pricing_agent_list' in fare_data:
                for pp in fare_data['pricing_agent_list']:
                    pricing_agent_ids.append((0, 0, pp))

            if pricing_provider_line_ids or pricing_agent_ids:
                self.write({
                    'pricing_provider_line_ids': pricing_provider_line_ids,
                    'pricing_agent_ids': pricing_agent_ids,
                })
        except:
            _logger.error('Error update pricing details, %s' % traceback.format_exc())
        return True

    # December 29, 2021 - SAM
    def action_send_vendor_ticket_email(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 108')
        if not self.provider_id:
            raise Exception('Provider is not set')
        req = {
            "provider": self.provider_id.code,
            "pnr": self.pnr,
            "pnr2": self.pnr2,
            "reference": self.reference,
            "ho_id": self.booking_id.agent_id.ho_id.id
        }
        res = self.env['tt.airline.api.con'].send_vendor_ticket_email(req)
        _logger.info('Action Send Vendor Ticket Email, %s-%s, %s' % (self.pnr, self.provider_id.code, json.dumps(res)))

        if res['error_code'] != 0:
            raise UserError('Send Vendor Ticket Email Failed, %s' % self.pnr)
        return True
    # END


class TtProviderAirlineRule(models.Model):
    _name = 'tt.provider.airline.rule'
    _description = 'Provider Airline Rule'

    name = fields.Char('Name', default='')
    description = fields.Text('Description', default='')
    provider_booking_id = fields.Many2one('tt.provider.airline', string='Provider Booking', ondelete='cascade')

    def to_dict(self):
        res = {
            'name': self.name if self.name else '',
            'description': [self.description] if self.description else [],
        }
        return res


class TtProviderAirlinePricing(models.Model):
    _name = 'tt.provider.airline.pricing'
    _description = 'Provider Airline Pricing'
    _order = 'id desc'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider', readonly=1)
    raw_data = fields.Text('Raw Data')

    rule_ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=1)
    rule_agent_id = fields.Many2one('tt.agent', 'Agent', readonly=1)
    rule_agent_type_code = fields.Char('Agent Type Code', readonly=1)
    rule_provider_type_code = fields.Char('Provider Type Code', readonly=1)
    rule_customer_parent_type_code = fields.Char('Customer Parent Type Code', readonly=1)
    rule_customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=1)
    rule_provider_code = fields.Char('Provider Code', readonly=1)
    rule_carrier_code = fields.Char('Carrier Code', readonly=1)
    rule_origin_code = fields.Char('Origin Code', readonly=1)
    rule_origin_city = fields.Char('Origin City Code', readonly=1)
    rule_origin_country = fields.Char('Origin Country Code', readonly=1)
    rule_destination_code = fields.Char('Destination Code', readonly=1)
    rule_destination_city = fields.Char('Destination City Code', readonly=1)
    rule_destination_country = fields.Char('Destination Country Code', readonly=1)
    rule_class_of_service_list = fields.Char('Class of Service Code List', readonly=1)
    rule_tour_code_list = fields.Char('Tour Code List', readonly=1)
    rule_charge_code_list = fields.Char('Charge Code List', readonly=1)
    rule_pricing_datetime = fields.Datetime('Pricing Datetime', readonly=1)
    rule_departure_date_list = fields.Char('Departure Date List', readonly=1, default='')
    rule_currency_code_list = fields.Char('Currency Code List', readonly=1, default='')
    rule_total_amount = fields.Char('Total Amount', readonly=1, default='')

    provider_pricing_id = fields.Many2one('tt.provider.pricing', 'Pricing ID', readonly=1, ondelete='set null')
    provider_pricing_sequence = fields.Char('Pricing Sequence', readonly=1)
    provider_pricing_index = fields.Char('Pricing Index', readonly=1)
    provider_type_code = fields.Char('Provider Type Code', readonly=1)
    provider_access_type = fields.Char('Provider Access Type', readonly=1)
    provider_code_list = fields.Char('Provider Code List', readonly=1)
    provider_carrier_access_type = fields.Char('Carrier Access Type', readonly=1)
    provider_carrier_code_list = fields.Char('Carrier Code List', readonly=1)
    provider_agent_access_type = fields.Char('Agent Access Type', readonly=1)
    provider_agent_id_list = fields.Char('Agent ID List', readonly=1)
    provider_agent_type_access_type = fields.Char('Agent Type Access Type', readonly=1)
    provider_agent_type_code_list = fields.Char('Agent Type Code List', readonly=1)
    provider_pricing_line_id = fields.Many2one('tt.provider.pricing.line', 'Pricing Line ID', readonly=1, ondelete='set null')
    provider_pricing_line_sequence = fields.Char('Pricing Line Sequence', readonly=1)
    provider_pricing_line_index = fields.Char('Pricing Line Index', readonly=1)
    provider_pricing_type = fields.Char('Pricing Type', readonly=1)
    provider_set_expiration_date = fields.Char('Set Expiration Date', readonly=1)
    provider_date_from = fields.Datetime('Date From', readonly=1)
    provider_date_to = fields.Datetime('Date To', readonly=1)
    provider_currency_code = fields.Char('Currency Code', readonly=1)
    provider_origin_access_type = fields.Char('Origin Access Type', readonly=1)
    provider_origin_code_list = fields.Char('Origin Code List', readonly=1)
    provider_origin_city_code_list = fields.Char('Origin City Code List', readonly=1)
    provider_origin_country_code_list = fields.Char('Origin Country Code List', readonly=1)
    provider_destination_access_type = fields.Char('Destination Access Type', readonly=1)
    provider_destination_code_list = fields.Char('Destination Code List', readonly=1)
    provider_destination_city_code_list = fields.Char('Destination City Code List', readonly=1)
    provider_destination_country_code_list = fields.Char('Destination Country Code List', readonly=1)
    provider_class_of_service_access_type = fields.Char('Class of Service Access Type', readonly=1)
    provider_class_of_service_list = fields.Char('Class of Service List', readonly=1)
    provider_charge_code_access_type = fields.Char('Charge Code Access Type', readonly=1)
    provider_charge_code_list = fields.Char('Charge Code List', readonly=1)
    provider_tour_code_access_type = fields.Char('Tour Code Access Type', readonly=1)
    provider_tour_code_list = fields.Char('Tour Code List', readonly=1)
    provider_dot_access_type = fields.Char('DOT Access Type', readonly=1)
    provider_dot_start_date = fields.Char('DOT Start Date', readonly=1)
    provider_dot_end_date = fields.Char('DOT End Date', readonly=1)
    provider_total_type = fields.Char('Total Access Type', readonly=1)
    provider_total_less_amount = fields.Char('Total Less Amount', readonly=1)
    provider_total_is_less_equal = fields.Char('Total Is Less Equal', readonly=1)
    provider_total_greater_amount = fields.Char('Total Greater Amount', readonly=1)
    provider_total_is_greater_equal = fields.Char('Total Is Greater Equal', readonly=1)
    provider_less_percentage = fields.Char('Vendor Less (%)', readonly=1)
    provider_less_infant = fields.Char('Apply less to Infant', readonly=1)
    provider_less_tour_code = fields.Char('Vendor Tour Code', readonly=1, default='')
    provider_tkt_nta_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_tkt_nta_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_tkt_nta_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_tkt_nta_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_tkt_nta_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_tkt_nta_total_amount = fields.Char('Total Amount', readonly=1)
    provider_tkt_nta_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_tkt_nta_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_tkt_nta_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_tkt_nta_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_tkt_nta_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_tkt_nta_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_tkt_nta_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_tkt_nta_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_tkt_nta_fare_infant = fields.Char('Apply Fare Pricing to Infant', readonly=1)
    provider_tkt_nta_tax_infant = fields.Char('Apply Tax Pricing to Infant', readonly=1)
    provider_tkt_nta_total_infant = fields.Char('Apply Total Pricing to Infant', readonly=1)
    provider_tkt_nta_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    provider_tkt_nta_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    provider_tkt_nta_agent_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_tkt_nta_agent_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_tkt_nta_agent_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_tkt_nta_agent_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_tkt_nta_agent_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_tkt_nta_agent_total_amount = fields.Char('Total Amount', readonly=1)
    provider_tkt_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_tkt_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_tkt_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_tkt_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_tkt_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_tkt_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_tkt_nta_agent_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_tkt_nta_agent_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_tkt_nta_agent_fare_infant = fields.Char('Apply Fare Pricing to Infant', readonly=1)
    provider_tkt_nta_agent_tax_infant = fields.Char('Apply Tax Pricing to Infant', readonly=1)
    provider_tkt_nta_agent_total_infant = fields.Char('Apply Total Pricing to Infant', readonly=1)
    provider_tkt_nta_agent_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    provider_tkt_nta_agent_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    provider_tkt_sales_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_tkt_sales_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_tkt_sales_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_tkt_sales_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_tkt_sales_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_tkt_sales_total_amount = fields.Char('Total Amount', readonly=1)
    provider_tkt_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_tkt_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_tkt_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_tkt_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_tkt_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_tkt_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_tkt_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_tkt_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_tkt_sales_fare_infant = fields.Char('Apply Fare Pricing to Infant', readonly=1)
    provider_tkt_sales_tax_infant = fields.Char('Apply Tax Pricing to Infant', readonly=1)
    provider_tkt_sales_total_infant = fields.Char('Apply Total Pricing to Infant', readonly=1)
    provider_tkt_sales_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    provider_tkt_sales_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    provider_anc_nta_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_anc_nta_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_anc_nta_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_anc_nta_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_anc_nta_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_anc_nta_total_amount = fields.Char('Total Amount', readonly=1)
    provider_anc_nta_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_anc_nta_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_anc_nta_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_anc_nta_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_anc_nta_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_anc_nta_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_anc_nta_agent_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_anc_nta_agent_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_anc_nta_agent_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_anc_nta_agent_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_anc_nta_agent_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_anc_nta_agent_total_amount = fields.Char('Total Amount', readonly=1)
    provider_anc_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_anc_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_anc_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_anc_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_anc_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_anc_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_anc_sales_fare_percentage = fields.Char('Fare (%)', readonly=1)
    provider_anc_sales_fare_amount = fields.Char('Fare Amount', readonly=1)
    provider_anc_sales_tax_percentage = fields.Char('Tax (%)', readonly=1)
    provider_anc_sales_tax_amount = fields.Char('Tax Amount', readonly=1)
    provider_anc_sales_total_percentage = fields.Char('Total (%)', readonly=1)
    provider_anc_sales_total_amount = fields.Char('Total Amount', readonly=1)
    provider_anc_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_anc_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_anc_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_anc_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_anc_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_anc_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_rsv_nta_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_rsv_nta_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_rsv_nta_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_rsv_nta_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_rsv_nta_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_rsv_nta_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_rsv_nta_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_rsv_nta_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_rsv_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_rsv_nta_agent_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_rsv_nta_agent_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_rsv_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_rsv_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_rsv_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_rsv_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_rsv_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_rsv_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    provider_rsv_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    provider_rsv_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    provider_rsv_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    provider_rsv_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    provider_rsv_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    provider_rsv_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    provider_rsv_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    provider_rsv_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    provider_rsv_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    provider_rsv_com_rounding = fields.Char('Commission Rounding', readonly=1)
    provider_tkt_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    provider_tkt_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    provider_tkt_com_rounding = fields.Char('Commission Rounding', readonly=1)
    provider_anc_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    provider_anc_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    provider_anc_com_rounding = fields.Char('Commission Rounding', readonly=1)
    provider_rsv_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    provider_rsv_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    provider_rsv_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    provider_tkt_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    provider_tkt_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    provider_tkt_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    provider_anc_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    provider_anc_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    provider_anc_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)

    agent_pricing_id = fields.Many2one('tt.agent.pricing', 'Agent Pricing', readonly=1, ondelete='set null')
    agent_pricing_sequence = fields.Char('Pricing Sequence', readonly=1)
    agent_pricing_index = fields.Char('Pricing Index', readonly=1)
    agent_provider_access_type = fields.Char('Provider Access Type', readonly=1)
    agent_provider_code_list = fields.Char('Provider Code List', readonly=1)
    agent_provider_type_access_type = fields.Char('Provider Type Access Type', readonly=1)
    agent_provider_type_code_list = fields.Char('Provider Type Code List', readonly=1)
    agent_carrier_access_type = fields.Char('Carrier Access Type', readonly=1)
    agent_carrier_code_list = fields.Char('Carrier Code List', readonly=1)
    agent_access_type = fields.Char('Agent Access Type', readonly=1)
    agent_id_list = fields.Char('Agent ID List', readonly=1)
    agent_type_access_type = fields.Char('Agent Type Access Type', readonly=1)
    agent_type_code_list = fields.Char('Agent Type Code List', readonly=1)
    agent_pricing_line_id = fields.Many2one('tt.agent.pricing.line', 'Agent Pricing Line', readonly=1, ondelete='set null')
    agent_pricing_line_sequence = fields.Char('Pricing Line Sequence', readonly=1)
    agent_pricing_line_index = fields.Char('Pricing Line Index', readonly=1)
    agent_set_expiration_date = fields.Char('Set Expiration Date', readonly=1)
    agent_date_from = fields.Datetime('Date From', readonly=1)
    agent_date_to = fields.Datetime('Date To', readonly=1)
    agent_currency_code = fields.Char('Currency Code', readonly=1)
    agent_origin_access_type = fields.Char('Origin Access Type', readonly=1)
    agent_origin_code_list = fields.Char('Origin Code List', readonly=1)
    agent_origin_city_code_list = fields.Char('Origin City Code List', readonly=1)
    agent_origin_country_code_list = fields.Char('Origin Country Code List', readonly=1)
    agent_destination_access_type = fields.Char('Destination Access Type', readonly=1)
    agent_destination_code_list = fields.Char('Destination Code List', readonly=1)
    agent_destination_city_code_list = fields.Char('Destination City Code List', readonly=1)
    agent_destination_country_code_list = fields.Char('Destination Country Code List', readonly=1)
    agent_class_of_service_access_type = fields.Char('Class of Service Access Type', readonly=1)
    agent_class_of_service_list = fields.Char('Class of Service List', readonly=1)
    agent_charge_code_access_type = fields.Char('Charge Code Access Type', readonly=1)
    agent_charge_code_list = fields.Char('Charge Code List', readonly=1)
    agent_tour_code_access_type = fields.Char('Tour Code Access Type', readonly=1)
    agent_tour_code_list = fields.Char('Tour Code List', readonly=1)
    agent_dot_access_type = fields.Char('DOT Access Type', readonly=1)
    agent_dot_start_date = fields.Char('DOT Start Date', readonly=1)
    agent_dot_end_date = fields.Char('DOT End Date', readonly=1)
    agent_total_type = fields.Char('Total Access Type', readonly=1)
    agent_total_less_amount = fields.Char('Total Less Amount', readonly=1)
    agent_total_is_less_equal = fields.Char('Total Is Less Equal', readonly=1)
    agent_total_greater_amount = fields.Char('Total Greater Amount', readonly=1)
    agent_total_is_greater_equal = fields.Char('Total Is Greater Equal', readonly=1)
    agent_parent_charge_percentage = fields.Char('Parent Charge (%)', readonly=1)
    agent_parent_charge_minimum = fields.Char('Parent Charge Minimum', readonly=1)
    agent_parent_charge_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_parent_charge_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_parent_charge_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_parent_charge_amount = fields.Char('Parent Charge Amount', readonly=1)
    agent_parent_charge_route = fields.Char('Parent Charge Route', readonly=1)
    agent_parent_charge_segment = fields.Char('Parent Charge Segment', readonly=1)
    agent_parent_charge_pax = fields.Char('Parent Charge Pax', readonly=1)
    agent_parent_charge_infant = fields.Char('Parent Charge Include Infant', readonly=1)
    agent_ho_charge_percentage = fields.Char('HO Charge (%)', readonly=1)
    agent_ho_charge_minimum = fields.Char('HO Charge Minimum', readonly=1)
    agent_ho_charge_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_ho_charge_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_ho_charge_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_ho_charge_amount = fields.Char('HO Charge Amount', readonly=1)
    agent_ho_charge_route = fields.Char('HO Charge Route', readonly=1)
    agent_ho_charge_segment = fields.Char('HO Charge Segment', readonly=1)
    agent_ho_charge_pax = fields.Char('HO Charge Pax', readonly=1)
    agent_ho_charge_infant = fields.Char('HO Charge Include Infant', readonly=1)
    agent_commission_percentage = fields.Char('Commission (%)', readonly=1)
    agent_commission_minimum = fields.Char('Commission Minimum', readonly=1)
    agent_commission_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_commission_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_commission_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_commission_amount = fields.Char('Commission Amount', readonly=1)
    agent_commission_route = fields.Char('Commission Route', readonly=1)
    agent_commission_segment = fields.Char('Commission Segment', readonly=1)
    agent_commission_pax = fields.Char('Commission Pax', readonly=1)
    agent_commission_infant = fields.Char('Commission Include Infant', readonly=1)
    agent_residual_amount_to = fields.Char('Residual Amount To', readonly=1)
    agent_tkt_sales_fare_percentage = fields.Char('Fare (%)', readonly=1)
    agent_tkt_sales_fare_amount = fields.Char('Fare Amount', readonly=1)
    agent_tkt_sales_tax_percentage = fields.Char('Tax (%)', readonly=1)
    agent_tkt_sales_tax_amount = fields.Char('Tax Amount', readonly=1)
    agent_tkt_sales_total_percentage = fields.Char('Total (%)', readonly=1)
    agent_tkt_sales_total_amount = fields.Char('Total Amount', readonly=1)
    agent_tkt_sales_fare_infant = fields.Char('Apply Fare Pricing to Infant', readonly=1)
    agent_tkt_sales_tax_infant = fields.Char('Apply Tax Pricing to Infant', readonly=1)
    agent_tkt_sales_total_infant = fields.Char('Apply Total Pricing to Infant', readonly=1)
    agent_tkt_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_tkt_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_tkt_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_tkt_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_tkt_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_tkt_sales_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    agent_tkt_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_tkt_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    agent_tkt_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    agent_tkt_sales_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    agent_anc_sales_fare_amount = fields.Char('Fare Amount', readonly=1)
    agent_anc_sales_tax_percentage = fields.Char('Tax (%)', readonly=1)
    agent_anc_sales_tax_amount = fields.Char('Tax Amount', readonly=1)
    agent_anc_sales_total_percentage = fields.Char('Total (%)', readonly=1)
    agent_anc_sales_total_amount = fields.Char('Total Amount', readonly=1)
    agent_anc_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_anc_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_anc_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_anc_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_anc_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_anc_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_rsv_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_rsv_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    agent_rsv_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    agent_rsv_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_rsv_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_rsv_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_rsv_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_rsv_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)

    agent_tkt_nta_agent_fare_percentage = fields.Char('Fare (%)', readonly=1)
    agent_tkt_nta_agent_fare_amount = fields.Char('Fare Amount', readonly=1)
    agent_tkt_nta_agent_tax_percentage = fields.Char('Tax (%)', readonly=1)
    agent_tkt_nta_agent_tax_amount = fields.Char('Tax Amount', readonly=1)
    agent_tkt_nta_agent_total_percentage = fields.Char('Total (%)', readonly=1)
    agent_tkt_nta_agent_total_amount = fields.Char('Total Amount', readonly=1)
    agent_tkt_nta_agent_fare_infant = fields.Char('Apply Fare Pricing to Infant', readonly=1)
    agent_tkt_nta_agent_tax_infant = fields.Char('Apply Tax Pricing to Infant', readonly=1)
    agent_tkt_nta_agent_total_infant = fields.Char('Apply Total Pricing to Infant', readonly=1)
    agent_tkt_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_tkt_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_tkt_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_tkt_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_tkt_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_tkt_nta_agent_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    agent_tkt_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_tkt_nta_agent_upsell_route = fields.Char('Upsell per Route', readonly=1)
    agent_tkt_nta_agent_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    agent_tkt_nta_agent_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    agent_anc_nta_agent_fare_amount = fields.Char('Fare Amount', readonly=1)
    agent_anc_nta_agent_tax_percentage = fields.Char('Tax (%)', readonly=1)
    agent_anc_nta_agent_tax_amount = fields.Char('Tax Amount', readonly=1)
    agent_anc_nta_agent_total_percentage = fields.Char('Total (%)', readonly=1)
    agent_anc_nta_agent_total_amount = fields.Char('Total Amount', readonly=1)
    agent_anc_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_anc_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_anc_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_anc_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_anc_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_anc_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_rsv_nta_agent_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    agent_rsv_nta_agent_upsell_route = fields.Char('Upsell per Route', readonly=1)
    agent_rsv_nta_agent_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    agent_rsv_nta_agent_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    agent_rsv_nta_agent_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    agent_rsv_nta_agent_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_rsv_nta_agent_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_rsv_nta_agent_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_rsv_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    agent_rsv_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    agent_rsv_com_rounding = fields.Char('Commission Rounding', readonly=1)
    agent_tkt_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    agent_tkt_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    agent_tkt_com_rounding = fields.Char('Commission Rounding', readonly=1)
    agent_anc_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    agent_anc_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    agent_anc_com_rounding = fields.Char('Commission Rounding', readonly=1)
    agent_rsv_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    agent_rsv_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    agent_rsv_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    agent_tkt_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    agent_tkt_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    agent_tkt_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    agent_anc_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    agent_anc_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    agent_anc_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)

    customer_pricing_id = fields.Many2one('tt.customer.pricing', 'Customer Pricing', readonly=1, ondelete='set null')
    customer_pricing_sequence = fields.Char('Pricing Sequence', readonly=1)
    customer_pricing_index = fields.Char('Pricing Index', readonly=1)
    customer_parent_access_type = fields.Char('Customer Parent Access Type', readonly=1)
    customer_parent_id_list = fields.Char('Customer Parent ID List', readonly=1)
    customer_parent_type_access_type = fields.Char('Customer Parent Type Access Type', readonly=1)
    customer_parent_type_code_list = fields.Char('Customer Parent Type Code List', readonly=1)
    customer_provider_access_type = fields.Char('Provider Access Type', readonly=1)
    customer_provider_code_list = fields.Char('Provider Code List', readonly=1)
    customer_provider_type_access_type = fields.Char('Provider Type Access Type', readonly=1)
    customer_provider_type_code_list = fields.Char('Provider Type Code List', readonly=1)
    customer_carrier_access_type = fields.Char('Carrier Access Type', readonly=1)
    customer_carrier_code_list = fields.Char('Carrier Code List', readonly=1)
    customer_pricing_line_id = fields.Many2one('tt.customer.pricing.line', 'Customer Pricing Line', readonly=1, ondelete='set null')
    customer_pricing_line_sequence = fields.Char('Pricing Line Sequence', readonly=1)
    customer_pricing_line_index = fields.Char('Pricing Line Index', readonly=1)
    customer_set_expiration_date = fields.Char('Set Expiration Date', readonly=1)
    customer_date_from = fields.Datetime('Date From', readonly=1)
    customer_date_to = fields.Datetime('Date To', readonly=1)
    customer_currency_code = fields.Char('Currency Code', readonly=1)
    customer_origin_access_type = fields.Char('Origin Access Type', readonly=1)
    customer_origin_code_list = fields.Char('Origin Code List', readonly=1)
    customer_origin_city_code_list = fields.Char('Origin City Code List', readonly=1)
    customer_origin_country_code_list = fields.Char('Origin Country Code List', readonly=1)
    customer_destination_access_type = fields.Char('Destination Access Type', readonly=1)
    customer_destination_code_list = fields.Char('Destination Code List', readonly=1)
    customer_destination_city_code_list = fields.Char('Destination City Code List', readonly=1)
    customer_destination_country_code_list = fields.Char('Destination Country Code List', readonly=1)
    customer_class_of_service_access_type = fields.Char('Class of Service Access Type', readonly=1)
    customer_class_of_service_list = fields.Char('Class of Service List', readonly=1)
    customer_charge_code_access_type = fields.Char('Charge Code Access Type', readonly=1)
    customer_charge_code_list = fields.Char('Charge Code List', readonly=1)
    customer_tour_code_access_type = fields.Char('Tour Code Access Type', readonly=1)
    customer_tour_code_list = fields.Char('Tour Code List', readonly=1)
    customer_dot_access_type = fields.Char('DOT Access Type', readonly=1)
    customer_dot_start_date = fields.Char('DOT Start Date', readonly=1)
    customer_dot_end_date = fields.Char('DOT End Date', readonly=1)
    customer_total_type = fields.Char('Total Access Type', readonly=1)
    customer_total_less_amount = fields.Char('Total Less Amount', readonly=1)
    customer_total_is_less_equal = fields.Char('Total Is Less Equal', readonly=1)
    customer_total_greater_amount = fields.Char('Total Greater Amount', readonly=1)
    customer_total_is_greater_equal = fields.Char('Total Is Greater Equal', readonly=1)
    customer_tkt_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    customer_tkt_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    customer_tkt_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    customer_tkt_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    customer_tkt_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    customer_tkt_sales_upsell_percentage_infant = fields.Char('Apply Upsell Percentage to Infant', readonly=1)
    customer_tkt_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    customer_tkt_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    customer_tkt_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    customer_tkt_sales_upsell_amount_infant = fields.Char('Apply Upsell Amount to Infant', readonly=1)
    customer_anc_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    customer_anc_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    customer_anc_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    customer_anc_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    customer_anc_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    customer_anc_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    customer_rsv_sales_upsell_amount = fields.Char('Upsell Amount', readonly=1)
    customer_rsv_sales_upsell_route = fields.Char('Upsell per Route', readonly=1)
    customer_rsv_sales_upsell_segment = fields.Char('Upsell per Segment', readonly=1)
    customer_rsv_sales_upsell_percentage = fields.Char('Upsell (%)', readonly=1)
    customer_rsv_sales_upsell_minimum = fields.Char('Minimum Amount', readonly=1)
    customer_rsv_sales_upsell_has_minimum = fields.Char('Has Minimum', readonly=1)
    customer_rsv_sales_upsell_maximum = fields.Char('Maximum Amount', readonly=1)
    customer_rsv_sales_upsell_has_maximum = fields.Char('Has Maximum', readonly=1)
    customer_rsv_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    customer_rsv_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    customer_rsv_com_rounding = fields.Char('Commission Rounding', readonly=1)
    customer_tkt_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    customer_tkt_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    customer_tkt_com_rounding = fields.Char('Commission Rounding', readonly=1)
    customer_anc_com_tax_amount = fields.Char('Commission Tax Amount', readonly=1)
    customer_anc_com_tax_percentage = fields.Char('Commission Tax Percentage', readonly=1)
    customer_anc_com_rounding = fields.Char('Commission Rounding', readonly=1)
    customer_rsv_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    customer_rsv_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    customer_rsv_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    customer_tkt_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    customer_tkt_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    customer_tkt_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)
    customer_anc_ho_com_tax_amount = fields.Char('HO Commission Tax Amount', readonly=1)
    customer_anc_ho_com_tax_percentage = fields.Char('HO Commission Tax Percentage', readonly=1)
    customer_anc_ho_com_rounding = fields.Char('HO Commission Rounding', readonly=1)

    agent_commission_id = fields.Many2one('tt.agent.commission', 'Agent Pricing', readonly=1, ondelete='set null')
    agent_commission_sequence = fields.Char('Pricing Sequence', readonly=1)
    agent_commission_index = fields.Char('Pricing Index', readonly=1)
    agent_commission_provider_access_type = fields.Char('Provider Access Type', readonly=1)
    agent_commission_provider_code_list = fields.Char('Provider Code List', readonly=1)
    agent_commission_provider_type_access_type = fields.Char('Provider Type Access Type', readonly=1)
    agent_commission_provider_type_code_list = fields.Char('Provider Type Code List', readonly=1)
    agent_commission_carrier_access_type = fields.Char('Carrier Access Type', readonly=1)
    agent_commission_carrier_code_list = fields.Char('Carrier Code List', readonly=1)
    agent_commission_access_type = fields.Char('Agent Access Type', readonly=1)
    agent_commission_id_list = fields.Char('Agent ID List', readonly=1)
    agent_commission_type_access_type = fields.Char('Agent Type Access Type', readonly=1)
    agent_commission_type_code_list = fields.Char('Agent Type Code List', readonly=1)
    agent_commission_line_id = fields.Many2one('tt.agent.commission.line', 'Agent Commission Line', readonly=1, ondelete='set null')
    agent_commission_line_sequence = fields.Char('Pricing Line Sequence', readonly=1)
    agent_commission_line_index = fields.Char('Pricing Line Index', readonly=1)
    agent_commission_set_expiration_date = fields.Char('Set Expiration Date', readonly=1)
    agent_commission_date_from = fields.Datetime('Date From', readonly=1)
    agent_commission_date_to = fields.Datetime('Date To', readonly=1)
    agent_commission_currency_code = fields.Char('Currency Code', readonly=1)
    agent_commission_origin_access_type = fields.Char('Origin Access Type', readonly=1)
    agent_commission_origin_code_list = fields.Char('Origin Code List', readonly=1)
    agent_commission_origin_city_code_list = fields.Char('Origin City Code List', readonly=1)
    agent_commission_origin_country_code_list = fields.Char('Origin Country Code List', readonly=1)
    agent_commission_destination_access_type = fields.Char('Destination Access Type', readonly=1)
    agent_commission_destination_code_list = fields.Char('Destination Code List', readonly=1)
    agent_commission_destination_city_code_list = fields.Char('Destination City Code List', readonly=1)
    agent_commission_destination_country_code_list = fields.Char('Destination Country Code List', readonly=1)
    agent_commission_class_of_service_access_type = fields.Char('Class of Service Access Type', readonly=1)
    agent_commission_class_of_service_list = fields.Char('Class of Service List', readonly=1)
    agent_commission_charge_code_access_type = fields.Char('Charge Code Access Type', readonly=1)
    agent_commission_charge_code_list = fields.Char('Charge Code List', readonly=1)
    agent_commission_tour_code_access_type = fields.Char('Tour Code Access Type', readonly=1)
    agent_commission_tour_code_list = fields.Char('Tour Code List', readonly=1)
    agent_commission_dot_access_type = fields.Char('DOT Access Type', readonly=1)
    agent_commission_dot_start_date = fields.Char('DOT Start Date', readonly=1)
    agent_commission_dot_end_date = fields.Char('DOT End Date', readonly=1)
    agent_commission_total_type = fields.Char('Total Access Type', readonly=1)
    agent_commission_total_less_amount = fields.Char('Total Less Amount', readonly=1)
    agent_commission_total_is_less_equal = fields.Char('Total Is Less Equal', readonly=1)
    agent_commission_total_greater_amount = fields.Char('Total Greater Amount', readonly=1)
    agent_commission_total_is_greater_equal = fields.Char('Total Is Greater Equal', readonly=1)
    agent_commission_parent_charge_percentage = fields.Char('Parent Charge (%)', readonly=1)
    agent_commission_parent_charge_minimum = fields.Char('Parent Charge Minimum', readonly=1)
    agent_commission_parent_charge_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_commission_parent_charge_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_commission_parent_charge_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_commission_parent_charge_amount = fields.Char('Parent Charge Amount', readonly=1)
    agent_commission_parent_charge_route = fields.Char('Parent Charge Route', readonly=1)
    agent_commission_parent_charge_segment = fields.Char('Parent Charge Segment', readonly=1)
    agent_commission_parent_charge_pax = fields.Char('Parent Charge Pax', readonly=1)
    agent_commission_parent_charge_infant = fields.Char('Parent Charge Include Infant', readonly=1)
    agent_commission_ho_charge_percentage = fields.Char('HO Charge (%)', readonly=1)
    agent_commission_ho_charge_minimum = fields.Char('HO Charge Minimum', readonly=1)
    agent_commission_ho_charge_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_commission_ho_charge_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_commission_ho_charge_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_commission_ho_charge_amount = fields.Char('HO Charge Amount', readonly=1)
    agent_commission_ho_charge_route = fields.Char('HO Charge Route', readonly=1)
    agent_commission_ho_charge_segment = fields.Char('HO Charge Segment', readonly=1)
    agent_commission_ho_charge_pax = fields.Char('HO Charge Pax', readonly=1)
    agent_commission_ho_charge_infant = fields.Char('HO Charge Include Infant', readonly=1)
    agent_commission_commission_percentage = fields.Char('Commission (%)', readonly=1)
    agent_commission_commission_minimum = fields.Char('Commission Minimum', readonly=1)
    agent_commission_commission_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_commission_commission_maximum = fields.Char('Maximum Amount', readonly=1)
    agent_commission_commission_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_commission_commission_amount = fields.Char('Commission Amount', readonly=1)
    agent_commission_commission_route = fields.Char('Commission Route', readonly=1)
    agent_commission_commission_segment = fields.Char('Commission Segment', readonly=1)
    agent_commission_commission_pax = fields.Char('Commission Pax', readonly=1)
    agent_commission_commission_infant = fields.Char('Commission Include Infant', readonly=1)
    agent_commission_residual_amount_to = fields.Char('Residual Amount To', readonly=1)
    upline_ids = fields.One2many('tt.provider.airline.pricing.upline', 'pricing_id', string='Uplines')

    agent_commission_discount_percentage = fields.Char('Discount (%)', readonly=1)
    agent_commission_discount_minimum = fields.Char('Discount Minimum', readonly=1)
    agent_commission_discount_has_minimum = fields.Char('Has Minimum', readonly=1)
    agent_commission_discount_maximum = fields.Char('Maximum Discount', readonly=1)
    agent_commission_discount_has_maximum = fields.Char('Has Maximum', readonly=1)
    agent_commission_discount_amount = fields.Char('Discount Amount', readonly=1)
    agent_commission_discount_route = fields.Char('Discount Route', readonly=1)
    agent_commission_discount_segment = fields.Char('Discount Segment', readonly=1)
    agent_commission_discount_pax = fields.Char('Discount Pax', readonly=1)
    agent_commission_discount_infant = fields.Char('Discount Include Infant', readonly=1)

    def convert_value(self, data=None, key=None, value=None):
        if isinstance(value, (str, int, float)) and type(value) != bool:
            pass
        elif type(value) == list:
            if not value or type(value[0]) != dict:
                rec_list = [str(rec) for rec in value]
                data[key] = ','.join(rec_list)
            else:
                for rec in value:
                    for n_key, n_value in rec.items():
                        self.convert_value(rec, n_key, n_value)
        elif type(value) == dict:
            for n_key, n_value in value.items():
                self.convert_value(value, n_key, n_value)
        else:
            data[key] = str(value)

    def compute_raw_data(self):
        if not self.raw_data:
            _logger.info('Compute Raw Data : NO DATA')
            return True

        _logger.info('Compute Raw Data : START')
        data = json.loads(self.raw_data)
        self.convert_value(value=data)

        rule_data = data.get('rule_data', {})
        provider_data = data.get('provider_pricing_data', {})
        agent_data = data.get('agent_pricing_data', {})
        customer_data = data.get('customer_pricing_data', {})
        agent_com_data = data.get('agent_commission_data', {})

        upline_ids = []
        for rec in self.upline_ids:
            upline_ids.append((2, rec.id))

        if agent_com_data:
            for rec_idx, rec in enumerate(agent_com_data['commission']['upline_list']):
                vals = {
                    'pricing_id': self.id,
                    'sequence': rec['sequence'],
                    'index': rec_idx,
                    'agent_type_code': rec['agent_type_code'],
                    'pricing_type': 'agent_commission',
                    'commission_percentage': rec['commission_by_percentage']['percentage'],
                    'commission_minimum': rec['commission_by_percentage']['minimum'],
                    'commission_has_minimum': rec['commission_by_percentage']['has_minimum'],
                    'commission_maximum': rec['commission_by_percentage']['maximum'],
                    'commission_has_maximum': rec['commission_by_percentage']['has_maximum'],
                    'commission_amount': rec['commission_by_amount']['amount'],
                    'commission_route': rec['commission_by_amount']['is_route'],
                    'commission_segment': rec['commission_by_amount']['is_segment'],
                    'commission_pax': rec['commission_by_amount']['is_pax'],
                    'commission_infant': rec['commission_by_amount']['is_infant'],
                }
                upline_ids.append((0, 0, vals))

        values = {
            'upline_ids': upline_ids
        }
        if rule_data:
            values.update({
                'rule_agent_id': rule_data['agent_id'],
                'rule_agent_type_code': rule_data['agent_type_code'],
                'rule_provider_type_code': rule_data['provider_type_code'],
                'rule_customer_parent_type_code': rule_data['customer_parent_type_code'],
                'rule_customer_parent_id': rule_data['customer_parent_id'],
                'rule_provider_code': rule_data['provider_code'],
                'rule_carrier_code': rule_data['carrier_code'],
                'rule_origin_code': rule_data['origin_code'],
                'rule_origin_city': rule_data['origin_city'],
                'rule_origin_country': rule_data['origin_country'],
                'rule_destination_code': rule_data['destination_code'],
                'rule_destination_city': rule_data['destination_city'],
                'rule_destination_country': rule_data['destination_country'],
                'rule_class_of_service_list': rule_data['class_of_service_list'],
                'rule_tour_code_list': rule_data['tour_code_list'],
                'rule_charge_code_list': rule_data['charge_code_list'],
                'rule_pricing_datetime': rule_data['pricing_datetime'],
                'rule_departure_date_list': rule_data.get('departure_date_list', ''),
                'rule_currency_code_list': rule_data.get('currency_code_list', ''),
                'rule_total_amount': rule_data.get('total_amount', ''),
            })

        if provider_data:
            prov_pricing_obj = self.env['tt.provider.pricing'].search([('id', '=', provider_data['pricing_id'])], limit=1)
            prov_pricing_line_obj = self.env['tt.provider.pricing.line'].search([('id', '=', provider_data['rule_id'])], limit=1)
            if prov_pricing_obj and prov_pricing_line_obj:
                values.update({
                    'provider_pricing_id': provider_data['pricing_id'],
                    'provider_pricing_sequence': provider_data['parent_data']['sequence'],
                    'provider_pricing_index': provider_data['pricing_index'],
                    'provider_type_code': provider_data['parent_data']['provider_type_code'],
                    'provider_access_type': provider_data['parent_data']['provider']['access_type'],
                    'provider_code_list': provider_data['parent_data']['provider']['provider_code_list'],
                    'provider_carrier_access_type': provider_data['parent_data']['carrier']['access_type'],
                    'provider_carrier_code_list': provider_data['parent_data']['carrier']['carrier_code_list'],
                    'provider_agent_access_type': provider_data['parent_data']['agent']['access_type'],
                    'provider_agent_id_list': provider_data['parent_data']['agent']['agent_id_list'],
                    'provider_agent_type_access_type': provider_data['parent_data']['agent_type']['access_type'],
                    'provider_agent_type_code_list': provider_data['parent_data']['agent_type']['agent_type_code_list'],
                    'provider_pricing_line_id': provider_data['rule_id'],
                    'provider_pricing_line_sequence': provider_data['sequence'],
                    'provider_pricing_line_index': provider_data['rule_index'],
                    'provider_pricing_type': provider_data.get('pricing_type', 'standard'),
                    'provider_currency_code': provider_data.get('currency_code', ''),
                    'provider_set_expiration_date': provider_data['set_expiration_date'],
                    'provider_date_from': provider_data['date_from'] if provider_data['date_from'] else None,
                    'provider_date_to': provider_data['date_to'] if provider_data['date_to'] else None,
                    'provider_origin_access_type': provider_data['route']['origin']['access_type'],
                    'provider_origin_code_list': provider_data['route']['origin']['destination_code_list'],
                    'provider_origin_city_code_list': provider_data['route']['origin']['city_code_list'],
                    'provider_origin_country_code_list': provider_data['route']['origin']['country_code_list'],
                    'provider_destination_access_type': provider_data['route']['destination']['access_type'],
                    'provider_destination_code_list': provider_data['route']['destination']['destination_code_list'],
                    'provider_destination_city_code_list': provider_data['route']['destination']['city_code_list'],
                    'provider_destination_country_code_list': provider_data['route']['destination']['country_code_list'],
                    'provider_class_of_service_access_type': provider_data['route']['class_of_service']['access_type'],
                    'provider_class_of_service_list': provider_data['route']['class_of_service']['class_of_service_list'],
                    'provider_charge_code_access_type': provider_data['route']['charge_code']['access_type'],
                    'provider_charge_code_list': provider_data['route']['charge_code']['charge_code_list'],
                    'provider_tour_code_access_type': provider_data['route']['charge_code']['access_type'],
                    'provider_tour_code_list': provider_data['route']['charge_code']['charge_code_list'],
                    'provider_dot_access_type': provider_data['route']['date_of_travel']['access_type'] if provider_data['route'].get('date_of_travel') else '',
                    'provider_dot_start_date': provider_data['route']['date_of_travel']['start_date'] if provider_data['route'].get('date_of_travel') else '',
                    'provider_dot_end_date': provider_data['route']['date_of_travel']['end_date'] if provider_data['route'].get('date_of_travel') else '',
                    'provider_less_percentage': provider_data['less']['percentage'],
                    'provider_less_infant': provider_data['less']['is_infant'],
                    'provider_less_tour_code': provider_data['less'].get('tour_code', ''),
                    'provider_tkt_nta_fare_percentage': provider_data['ticketing']['nta']['fare']['percentage'],
                    'provider_tkt_nta_fare_amount': provider_data['ticketing']['nta']['fare']['amount'],
                    'provider_tkt_nta_tax_percentage': provider_data['ticketing']['nta']['tax']['percentage'],
                    'provider_tkt_nta_tax_amount': provider_data['ticketing']['nta']['tax']['amount'],
                    'provider_tkt_nta_total_percentage': provider_data['ticketing']['nta']['total']['percentage'],
                    'provider_tkt_nta_total_amount': provider_data['ticketing']['nta']['total']['amount'],
                    'provider_tkt_nta_upsell_percentage': provider_data['ticketing']['nta']['upsell_by_percentage']['percentage'],
                    'provider_tkt_nta_upsell_minimum': provider_data['ticketing']['nta']['upsell_by_percentage']['minimum'],
                    'provider_tkt_nta_upsell_has_minimum': provider_data['ticketing']['nta']['upsell_by_percentage']['has_minimum'],
                    'provider_tkt_nta_upsell_maximum': provider_data['ticketing']['nta']['upsell_by_percentage']['maximum'],
                    'provider_tkt_nta_upsell_has_maximum': provider_data['ticketing']['nta']['upsell_by_percentage']['has_maximum'],
                    'provider_tkt_nta_upsell_amount': provider_data['ticketing']['nta']['upsell_by_amount']['amount'],
                    'provider_tkt_nta_upsell_route': provider_data['ticketing']['nta']['upsell_by_amount']['is_route'],
                    'provider_tkt_nta_upsell_segment': provider_data['ticketing']['nta']['upsell_by_amount']['is_segment'],
                    'provider_tkt_nta_fare_infant': provider_data['ticketing']['nta']['fare']['is_infant'],
                    'provider_tkt_nta_tax_infant': provider_data['ticketing']['nta']['tax']['is_infant'],
                    'provider_tkt_nta_total_infant': provider_data['ticketing']['nta']['total']['is_infant'],
                    'provider_tkt_nta_upsell_percentage_infant': provider_data['ticketing']['nta']['upsell_by_percentage']['is_infant'],
                    'provider_tkt_nta_upsell_amount_infant': provider_data['ticketing']['nta']['upsell_by_amount']['is_infant'],
                    'provider_tkt_nta_agent_fare_percentage': provider_data['ticketing']['nta_agent']['fare']['percentage'],
                    'provider_tkt_nta_agent_fare_amount': provider_data['ticketing']['nta_agent']['fare']['amount'],
                    'provider_tkt_nta_agent_tax_percentage': provider_data['ticketing']['nta_agent']['tax']['percentage'],
                    'provider_tkt_nta_agent_tax_amount': provider_data['ticketing']['nta_agent']['tax']['amount'],
                    'provider_tkt_nta_agent_total_percentage': provider_data['ticketing']['nta_agent']['total']['percentage'],
                    'provider_tkt_nta_agent_total_amount': provider_data['ticketing']['nta_agent']['total']['amount'],
                    'provider_tkt_nta_agent_upsell_percentage': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['percentage'],
                    'provider_tkt_nta_agent_upsell_minimum': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['minimum'],
                    'provider_tkt_nta_agent_upsell_has_minimum': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'provider_tkt_nta_agent_upsell_maximum': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['maximum'],
                    'provider_tkt_nta_agent_upsell_has_maximum': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['has_maximum'],
                    'provider_tkt_nta_agent_upsell_amount': provider_data['ticketing']['nta_agent']['upsell_by_amount']['amount'],
                    'provider_tkt_nta_agent_upsell_route': provider_data['ticketing']['nta_agent']['upsell_by_amount']['is_route'],
                    'provider_tkt_nta_agent_upsell_segment': provider_data['ticketing']['nta_agent']['upsell_by_amount']['is_segment'],
                    'provider_tkt_nta_agent_fare_infant': provider_data['ticketing']['nta_agent']['fare']['is_infant'],
                    'provider_tkt_nta_agent_tax_infant': provider_data['ticketing']['nta_agent']['tax']['is_infant'],
                    'provider_tkt_nta_agent_total_infant': provider_data['ticketing']['nta_agent']['total']['is_infant'],
                    'provider_tkt_nta_agent_upsell_percentage_infant': provider_data['ticketing']['nta_agent']['upsell_by_percentage']['is_infant'],
                    'provider_tkt_nta_agent_upsell_amount_infant': provider_data['ticketing']['nta_agent']['upsell_by_amount']['is_infant'],
                    'provider_tkt_sales_fare_percentage': provider_data['ticketing']['sales']['fare']['percentage'],
                    'provider_tkt_sales_fare_amount': provider_data['ticketing']['sales']['fare']['amount'],
                    'provider_tkt_sales_tax_percentage': provider_data['ticketing']['sales']['tax']['percentage'],
                    'provider_tkt_sales_tax_amount': provider_data['ticketing']['sales']['tax']['amount'],
                    'provider_tkt_sales_total_percentage': provider_data['ticketing']['sales']['total']['percentage'],
                    'provider_tkt_sales_total_amount': provider_data['ticketing']['sales']['total']['amount'],
                    'provider_tkt_sales_upsell_percentage': provider_data['ticketing']['sales']['upsell_by_percentage']['percentage'],
                    'provider_tkt_sales_upsell_minimum': provider_data['ticketing']['sales']['upsell_by_percentage']['minimum'],
                    'provider_tkt_sales_upsell_has_minimum': provider_data['ticketing']['sales']['upsell_by_percentage']['has_minimum'],
                    'provider_tkt_sales_upsell_maximum': provider_data['ticketing']['sales']['upsell_by_percentage']['maximum'],
                    'provider_tkt_sales_upsell_has_maximum': provider_data['ticketing']['sales']['upsell_by_percentage']['has_maximum'],
                    'provider_tkt_sales_upsell_amount': provider_data['ticketing']['sales']['upsell_by_amount']['amount'],
                    'provider_tkt_sales_upsell_route': provider_data['ticketing']['sales']['upsell_by_amount']['is_route'],
                    'provider_tkt_sales_upsell_segment': provider_data['ticketing']['sales']['upsell_by_amount']['is_segment'],
                    'provider_tkt_sales_fare_infant': provider_data['ticketing']['sales']['fare']['is_infant'],
                    'provider_tkt_sales_tax_infant': provider_data['ticketing']['sales']['tax']['is_infant'],
                    'provider_tkt_sales_total_infant': provider_data['ticketing']['sales']['total']['is_infant'],
                    'provider_tkt_sales_upsell_percentage_infant': provider_data['ticketing']['sales']['upsell_by_percentage']['is_infant'],
                    'provider_tkt_sales_upsell_amount_infant': provider_data['ticketing']['sales']['upsell_by_amount']['is_infant'],
                    'provider_anc_nta_fare_percentage': provider_data['ancillary']['nta']['fare']['percentage'],
                    'provider_anc_nta_fare_amount': provider_data['ancillary']['nta']['fare']['amount'],
                    'provider_anc_nta_tax_percentage': provider_data['ancillary']['nta']['tax']['percentage'],
                    'provider_anc_nta_tax_amount': provider_data['ancillary']['nta']['tax']['amount'],
                    'provider_anc_nta_total_percentage': provider_data['ancillary']['nta']['total']['percentage'],
                    'provider_anc_nta_total_amount': provider_data['ancillary']['nta']['total']['amount'],
                    'provider_anc_nta_upsell_percentage': provider_data['ancillary']['nta']['upsell_by_percentage']['percentage'],
                    'provider_anc_nta_upsell_minimum': provider_data['ancillary']['nta']['upsell_by_percentage']['minimum'],
                    'provider_anc_nta_upsell_has_minimum': provider_data['ancillary']['nta']['upsell_by_percentage']['has_minimum'],
                    'provider_anc_nta_upsell_maximum': provider_data['ancillary']['nta']['upsell_by_percentage']['maximum'],
                    'provider_anc_nta_upsell_has_maximum': provider_data['ancillary']['nta']['upsell_by_percentage']['has_maximum'],
                    'provider_anc_nta_upsell_amount': provider_data['ancillary']['nta']['upsell_by_amount']['amount'],
                    'provider_anc_nta_agent_fare_percentage': provider_data['ancillary']['nta_agent']['fare']['percentage'],
                    'provider_anc_nta_agent_fare_amount': provider_data['ancillary']['nta_agent']['fare']['amount'],
                    'provider_anc_nta_agent_tax_percentage': provider_data['ancillary']['nta_agent']['tax']['percentage'],
                    'provider_anc_nta_agent_tax_amount': provider_data['ancillary']['nta_agent']['tax']['amount'],
                    'provider_anc_nta_agent_total_percentage': provider_data['ancillary']['nta_agent']['total']['percentage'],
                    'provider_anc_nta_agent_total_amount': provider_data['ancillary']['nta_agent']['total']['amount'],
                    'provider_anc_nta_agent_upsell_percentage': provider_data['ancillary']['nta_agent']['upsell_by_percentage']['percentage'],
                    'provider_anc_nta_agent_upsell_minimum': provider_data['ancillary']['nta_agent']['upsell_by_percentage']['minimum'],
                    'provider_anc_nta_agent_upsell_has_minimum': provider_data['ancillary']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'provider_anc_nta_agent_upsell_maximum': provider_data['ancillary']['nta_agent']['upsell_by_percentage']['maximum'],
                    'provider_anc_nta_agent_upsell_has_maximum': provider_data['ancillary']['nta_agent']['upsell_by_percentage']['has_maximum'],
                    'provider_anc_nta_agent_upsell_amount': provider_data['ancillary']['nta_agent']['upsell_by_amount']['amount'],
                    'provider_anc_sales_fare_percentage': provider_data['ancillary']['sales']['fare']['percentage'],
                    'provider_anc_sales_fare_amount': provider_data['ancillary']['sales']['fare']['amount'],
                    'provider_anc_sales_tax_percentage': provider_data['ancillary']['sales']['tax']['percentage'],
                    'provider_anc_sales_tax_amount': provider_data['ancillary']['sales']['tax']['amount'],
                    'provider_anc_sales_total_percentage': provider_data['ancillary']['sales']['total']['percentage'],
                    'provider_anc_sales_total_amount': provider_data['ancillary']['sales']['total']['amount'],
                    'provider_anc_sales_upsell_percentage': provider_data['ancillary']['sales']['upsell_by_percentage']['percentage'],
                    'provider_anc_sales_upsell_minimum': provider_data['ancillary']['sales']['upsell_by_percentage']['minimum'],
                    'provider_anc_sales_upsell_has_minimum': provider_data['ancillary']['sales']['upsell_by_percentage']['has_minimum'],
                    'provider_anc_sales_upsell_maximum': provider_data['ancillary']['sales']['upsell_by_percentage']['maximum'],
                    'provider_anc_sales_upsell_has_maximum': provider_data['ancillary']['sales']['upsell_by_percentage']['has_maximum'],
                    'provider_anc_sales_upsell_amount': provider_data['ancillary']['sales']['upsell_by_amount']['amount'],
                    'provider_rsv_nta_upsell_amount': provider_data['reservation']['nta']['upsell_by_amount']['amount'],
                    'provider_rsv_nta_upsell_route': provider_data['reservation']['nta']['upsell_by_amount']['is_route'],
                    'provider_rsv_nta_upsell_segment': provider_data['reservation']['nta']['upsell_by_amount']['is_segment'],
                    'provider_rsv_nta_upsell_percentage': provider_data['reservation']['nta']['upsell_by_percentage']['percentage'],
                    'provider_rsv_nta_upsell_minimum': provider_data['reservation']['nta']['upsell_by_percentage']['minimum'],
                    'provider_rsv_nta_upsell_has_minimum': provider_data['reservation']['nta']['upsell_by_percentage']['has_minimum'],
                    'provider_rsv_nta_upsell_maximum': provider_data['reservation']['nta']['upsell_by_percentage']['maximum'],
                    'provider_rsv_nta_upsell_has_maximum': provider_data['reservation']['nta']['upsell_by_percentage']['has_maximum'],
                    'provider_rsv_nta_agent_upsell_amount': provider_data['reservation']['nta_agent']['upsell_by_amount']['amount'],
                    'provider_rsv_nta_agent_upsell_route': provider_data['reservation']['nta_agent']['upsell_by_amount']['is_route'],
                    'provider_rsv_nta_agent_upsell_segment': provider_data['reservation']['nta_agent']['upsell_by_amount']['is_segment'],
                    'provider_rsv_nta_agent_upsell_percentage': provider_data['reservation']['nta_agent']['upsell_by_percentage']['percentage'],
                    'provider_rsv_nta_agent_upsell_minimum': provider_data['reservation']['nta_agent']['upsell_by_percentage']['minimum'],
                    'provider_rsv_nta_agent_upsell_has_minimum': provider_data['reservation']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'provider_rsv_nta_agent_upsell_maximum': provider_data['reservation']['nta_agent']['upsell_by_percentage']['maximum'],
                    'provider_rsv_nta_agent_upsell_has_maximum': provider_data['reservation']['nta_agent']['upsell_by_percentage']['has_maximum'],
                    'provider_rsv_sales_upsell_amount': provider_data['reservation']['sales']['upsell_by_amount']['amount'],
                    'provider_rsv_sales_upsell_route': provider_data['reservation']['sales']['upsell_by_amount']['is_route'],
                    'provider_rsv_sales_upsell_segment': provider_data['reservation']['sales']['upsell_by_amount']['is_segment'],
                    'provider_rsv_sales_upsell_percentage': provider_data['reservation']['sales']['upsell_by_percentage']['percentage'],
                    'provider_rsv_sales_upsell_minimum': provider_data['reservation']['sales']['upsell_by_percentage']['minimum'],
                    'provider_rsv_sales_upsell_has_minimum': provider_data['reservation']['sales']['upsell_by_percentage']['has_minimum'],
                    'provider_rsv_sales_upsell_maximum': provider_data['reservation']['sales']['upsell_by_percentage']['maximum'],
                    'provider_rsv_sales_upsell_has_maximum': provider_data['reservation']['sales']['upsell_by_percentage']['has_maximum'],
                })
                if provider_data['reservation'].get('commission'):
                    values.update({
                        'provider_rsv_com_tax_amount': provider_data['reservation']['commission'].get('tax_amount', ''),
                        'provider_rsv_com_tax_percentage': provider_data['reservation']['commission'].get('tax_percentage', ''),
                        'provider_rsv_com_rounding': provider_data['reservation']['commission'].get('rounding', ''),
                    })
                if provider_data['ticketing'].get('commission'):
                    values.update({
                        'provider_tkt_com_tax_amount': provider_data['ticketing']['commission'].get('tax_amount', ''),
                        'provider_tkt_com_tax_percentage': provider_data['ticketing']['commission'].get('tax_percentage', ''),
                        'provider_tkt_com_rounding': provider_data['ticketing']['commission'].get('rounding', ''),
                    })
                if provider_data['ancillary'].get('commission'):
                    values.update({
                        'provider_anc_com_tax_amount': provider_data['ancillary']['commission'].get('tax_amount', ''),
                        'provider_anc_com_tax_percentage': provider_data['ancillary']['commission'].get('tax_percentage', ''),
                        'provider_anc_com_rounding': provider_data['ancillary']['commission'].get('rounding', ''),
                    })
                if provider_data['reservation'].get('ho_commission'):
                    values.update({
                        'provider_rsv_ho_com_tax_amount': provider_data['reservation']['ho_commission'].get('tax_amount', ''),
                        'provider_rsv_ho_com_tax_percentage': provider_data['reservation']['ho_commission'].get('tax_percentage', ''),
                        'provider_rsv_ho_com_rounding': provider_data['reservation']['ho_commission'].get('rounding', ''),
                    })
                if provider_data['ticketing'].get('ho_commission'):
                    values.update({
                        'provider_tkt_ho_com_tax_amount': provider_data['ticketing']['ho_commission'].get('tax_amount', ''),
                        'provider_tkt_ho_com_tax_percentage': provider_data['ticketing']['ho_commission'].get('tax_percentage', ''),
                        'provider_tkt_ho_com_rounding': provider_data['ticketing']['ho_commission'].get('rounding', ''),
                    })
                if provider_data['ancillary'].get('ho_commission'):
                    values.update({
                        'provider_anc_ho_com_tax_amount': provider_data['ancillary']['ho_commission'].get('tax_amount', ''),
                        'provider_anc_ho_com_tax_percentage': provider_data['ancillary']['ho_commission'].get('tax_percentage', ''),
                        'provider_anc_ho_com_rounding': provider_data['ancillary']['ho_commission'].get('rounding', ''),
                    })

                if provider_data['route'].get('total', {}):
                    values.update({
                        'provider_total_type': provider_data['route']['total'].get('access_type', ''),
                        'provider_total_less_amount': provider_data['route']['total'].get('less_amount', ''),
                        'provider_total_is_less_equal': provider_data['route']['total'].get('is_less_equal', ''),
                        'provider_total_greater_amount': provider_data['route']['total'].get('greater_amount', ''),
                        'provider_total_is_greater_equal': provider_data['route']['total'].get('is_greater_equal', ''),
                    })

        if agent_data:
            agent_pricing_obj = self.env['tt.agent.pricing'].search([('id', '=', agent_data['pricing_id'])], limit=1)
            agent_pricing_line_obj = self.env['tt.agent.pricing.line'].search([('id', '=', agent_data['rule_id'])], limit=1)
            if agent_pricing_obj and agent_pricing_line_obj:
                values.update({
                    'agent_pricing_id': agent_data['pricing_id'],
                    'agent_pricing_sequence': agent_data['parent_data']['sequence'],
                    'agent_pricing_index': agent_data['pricing_index'],
                    'agent_provider_access_type': agent_data['parent_data']['provider']['access_type'],
                    'agent_provider_code_list': agent_data['parent_data']['provider']['provider_code_list'],
                    'agent_provider_type_access_type': agent_data['parent_data']['provider_type']['access_type'],
                    'agent_provider_type_code_list': agent_data['parent_data']['provider_type']['provider_type_code_list'],
                    'agent_carrier_access_type': agent_data['parent_data']['carrier']['access_type'],
                    'agent_carrier_code_list': agent_data['parent_data']['carrier']['carrier_code_list'],
                    'agent_access_type': agent_data['parent_data']['agent']['access_type'],
                    'agent_id_list': agent_data['parent_data']['agent']['agent_id_list'],
                    'agent_type_access_type': agent_data['parent_data']['agent_type']['access_type'],
                    'agent_type_code_list': agent_data['parent_data']['agent_type']['agent_type_code_list'],
                    'agent_pricing_line_id': agent_data['rule_id'],
                    'agent_pricing_line_sequence': agent_data['sequence'],
                    'agent_pricing_line_index': agent_data['rule_index'],
                    'agent_currency_code': agent_data.get('currency_code', ''),
                    'agent_set_expiration_date': agent_data['set_expiration_date'],
                    'agent_date_from': agent_data['date_from'] if agent_data['date_from'] else None,
                    'agent_date_to': agent_data['date_to'] if agent_data['date_to'] else None,
                    'agent_origin_access_type': agent_data['route']['origin']['access_type'],
                    'agent_origin_code_list': agent_data['route']['origin']['destination_code_list'],
                    'agent_origin_city_code_list': agent_data['route']['origin']['city_code_list'],
                    'agent_origin_country_code_list': agent_data['route']['origin']['country_code_list'],
                    'agent_destination_access_type': agent_data['route']['destination']['access_type'],
                    'agent_destination_code_list': agent_data['route']['destination']['destination_code_list'],
                    'agent_destination_city_code_list': agent_data['route']['destination']['city_code_list'],
                    'agent_destination_country_code_list': agent_data['route']['destination']['country_code_list'],
                    'agent_class_of_service_access_type': agent_data['route']['class_of_service']['access_type'],
                    'agent_class_of_service_list': agent_data['route']['class_of_service']['class_of_service_list'],
                    'agent_charge_code_access_type': agent_data['route']['charge_code']['access_type'],
                    'agent_charge_code_list': agent_data['route']['charge_code']['charge_code_list'],
                    'agent_tour_code_access_type': agent_data['route']['charge_code']['access_type'],
                    'agent_tour_code_list': agent_data['route']['charge_code']['charge_code_list'],
                    'agent_dot_access_type': agent_data['route']['date_of_travel']['access_type'] if agent_data['route'].get('date_of_travel') else '',
                    'agent_dot_start_date': agent_data['route']['date_of_travel']['start_date'] if agent_data['route'].get('date_of_travel') else '',
                    'agent_dot_end_date': agent_data['route']['date_of_travel']['end_date'] if agent_data['route'].get('date_of_travel') else '',
                    # 'agent_parent_charge_percentage': '',
                    # 'agent_parent_charge_minimum': '',
                    # 'agent_parent_charge_has_minimum': '',
                    # 'agent_parent_charge_maximum': '',
                    # 'agent_parent_charge_has_maximum': '',
                    # 'agent_parent_charge_amount': '',
                    # 'agent_parent_charge_route': '',
                    # 'agent_parent_charge_segment': '',
                    # 'agent_parent_charge_pax': '',
                    # 'agent_parent_charge_infant': '',
                    # 'agent_ho_charge_percentage': '',
                    # 'agent_ho_charge_minimum': '',
                    # 'agent_ho_charge_has_minimum': '',
                    # 'agent_ho_charge_maximum': '',
                    # 'agent_ho_charge_has_maximum': '',
                    # 'agent_ho_charge_amount': '',
                    # 'agent_ho_charge_route': '',
                    # 'agent_ho_charge_segment': '',
                    # 'agent_ho_charge_pax': '',
                    # 'agent_ho_charge_infant': '',
                    # 'agent_commission_percentage': '',
                    # 'agent_commission_minimum': '',
                    # 'agent_commission_has_minimum': '',
                    # 'agent_commission_maximum': '',
                    # 'agent_commission_has_maximum': '',
                    # 'agent_commission_amount': '',
                    # 'agent_commission_route': '',
                    # 'agent_commission_segment': '',
                    # 'agent_commission_pax': '',
                    # 'agent_commission_infant': '',
                    # 'agent_residual_amount_to': '',
                    'agent_tkt_sales_fare_percentage': agent_data['ticketing']['sales']['fare']['percentage'],
                    'agent_tkt_sales_fare_amount': agent_data['ticketing']['sales']['fare']['amount'],
                    'agent_tkt_sales_tax_percentage': agent_data['ticketing']['sales']['tax']['percentage'],
                    'agent_tkt_sales_tax_amount': agent_data['ticketing']['sales']['tax']['amount'],
                    'agent_tkt_sales_total_percentage': agent_data['ticketing']['sales']['total']['percentage'],
                    'agent_tkt_sales_total_amount': agent_data['ticketing']['sales']['total']['amount'],
                    'agent_tkt_sales_fare_infant': agent_data['ticketing']['sales']['fare']['is_infant'],
                    'agent_tkt_sales_tax_infant': agent_data['ticketing']['sales']['tax']['is_infant'],
                    'agent_tkt_sales_total_infant': agent_data['ticketing']['sales']['total']['is_infant'],
                    'agent_tkt_sales_upsell_percentage': agent_data['ticketing']['sales']['upsell_by_percentage']['percentage'],
                    'agent_tkt_sales_upsell_minimum': agent_data['ticketing']['sales']['upsell_by_percentage']['minimum'],
                    'agent_tkt_sales_upsell_has_minimum': agent_data['ticketing']['sales']['upsell_by_percentage']['has_minimum'],
                    'agent_tkt_sales_upsell_maximum': agent_data['ticketing']['sales']['upsell_by_percentage']['maximum'],
                    'agent_tkt_sales_upsell_has_maximum': agent_data['ticketing']['sales']['upsell_by_percentage']['has_maximum'],
                    'agent_tkt_sales_upsell_percentage_infant': agent_data['ticketing']['sales']['upsell_by_percentage']['is_infant'],
                    'agent_tkt_sales_upsell_amount': agent_data['ticketing']['sales']['upsell_by_amount']['amount'],
                    'agent_tkt_sales_upsell_route': agent_data['ticketing']['sales']['upsell_by_amount']['is_route'],
                    'agent_tkt_sales_upsell_segment': agent_data['ticketing']['sales']['upsell_by_amount']['is_segment'],
                    'agent_tkt_sales_upsell_amount_infant': agent_data['ticketing']['sales']['upsell_by_amount']['is_infant'],
                    'agent_anc_sales_fare_percentage': agent_data['ancillary']['sales']['fare']['percentage'],
                    'agent_anc_sales_fare_amount': agent_data['ancillary']['sales']['fare']['amount'],
                    'agent_anc_sales_tax_percentage': agent_data['ancillary']['sales']['tax']['percentage'],
                    'agent_anc_sales_tax_amount': agent_data['ancillary']['sales']['tax']['amount'],
                    'agent_anc_sales_total_percentage': agent_data['ancillary']['sales']['total']['percentage'],
                    'agent_anc_sales_total_amount': agent_data['ancillary']['sales']['total']['amount'],
                    'agent_anc_sales_upsell_percentage': agent_data['ancillary']['sales']['upsell_by_percentage']['percentage'],
                    'agent_anc_sales_upsell_minimum': agent_data['ancillary']['sales']['upsell_by_percentage']['minimum'],
                    'agent_anc_sales_upsell_has_minimum': agent_data['ancillary']['sales']['upsell_by_percentage']['has_minimum'],
                    'agent_anc_sales_upsell_maximum': agent_data['ancillary']['sales']['upsell_by_percentage']['maximum'],
                    'agent_anc_sales_upsell_has_maximum': agent_data['ancillary']['sales']['upsell_by_percentage']['has_maximum'],
                    'agent_anc_sales_upsell_amount': agent_data['ancillary']['sales']['upsell_by_amount']['amount'],
                    'agent_rsv_sales_upsell_amount': agent_data['reservation']['sales']['upsell_by_amount']['amount'],
                    'agent_rsv_sales_upsell_route': agent_data['reservation']['sales']['upsell_by_amount']['is_route'],
                    'agent_rsv_sales_upsell_segment': agent_data['reservation']['sales']['upsell_by_amount']['is_segment'],
                    'agent_rsv_sales_upsell_percentage': agent_data['reservation']['sales']['upsell_by_percentage']['percentage'],
                    'agent_rsv_sales_upsell_minimum': agent_data['reservation']['sales']['upsell_by_percentage']['minimum'],
                    'agent_rsv_sales_upsell_has_minimum': agent_data['reservation']['sales']['upsell_by_percentage']['has_minimum'],
                    'agent_rsv_sales_upsell_maximum': agent_data['reservation']['sales']['upsell_by_percentage']['maximum'],
                    'agent_rsv_sales_upsell_has_maximum': agent_data['reservation']['sales']['upsell_by_percentage']['has_maximum'],
                    'agent_tkt_nta_agent_fare_percentage': agent_data['ticketing']['nta_agent']['fare']['percentage'],
                    'agent_tkt_nta_agent_fare_amount': agent_data['ticketing']['nta_agent']['fare']['amount'],
                    'agent_tkt_nta_agent_tax_percentage': agent_data['ticketing']['nta_agent']['tax']['percentage'],
                    'agent_tkt_nta_agent_tax_amount': agent_data['ticketing']['nta_agent']['tax']['amount'],
                    'agent_tkt_nta_agent_total_percentage': agent_data['ticketing']['nta_agent']['total']['percentage'],
                    'agent_tkt_nta_agent_total_amount': agent_data['ticketing']['nta_agent']['total']['amount'],
                    'agent_tkt_nta_agent_fare_infant': agent_data['ticketing']['nta_agent']['fare']['is_infant'],
                    'agent_tkt_nta_agent_tax_infant': agent_data['ticketing']['nta_agent']['tax']['is_infant'],
                    'agent_tkt_nta_agent_total_infant': agent_data['ticketing']['nta_agent']['total']['is_infant'],
                    'agent_tkt_nta_agent_upsell_percentage': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['percentage'],
                    'agent_tkt_nta_agent_upsell_minimum': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['minimum'],
                    'agent_tkt_nta_agent_upsell_has_minimum': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'agent_tkt_nta_agent_upsell_maximum': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['maximum'],
                    'agent_tkt_nta_agent_upsell_has_maximum': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['has_maximum'],
                    'agent_tkt_nta_agent_upsell_percentage_infant': agent_data['ticketing']['nta_agent']['upsell_by_percentage']['is_infant'],
                    'agent_tkt_nta_agent_upsell_amount': agent_data['ticketing']['nta_agent']['upsell_by_amount']['amount'],
                    'agent_tkt_nta_agent_upsell_route': agent_data['ticketing']['nta_agent']['upsell_by_amount']['is_route'],
                    'agent_tkt_nta_agent_upsell_segment': agent_data['ticketing']['nta_agent']['upsell_by_amount']['is_segment'],
                    'agent_tkt_nta_agent_upsell_amount_infant': agent_data['ticketing']['nta_agent']['upsell_by_amount']['is_infant'],
                    'agent_anc_nta_agent_fare_percentage': agent_data['ancillary']['nta_agent']['fare']['percentage'],
                    'agent_anc_nta_agent_fare_amount': agent_data['ancillary']['nta_agent']['fare']['amount'],
                    'agent_anc_nta_agent_tax_percentage': agent_data['ancillary']['nta_agent']['tax']['percentage'],
                    'agent_anc_nta_agent_tax_amount': agent_data['ancillary']['nta_agent']['tax']['amount'],
                    'agent_anc_nta_agent_total_percentage': agent_data['ancillary']['nta_agent']['total']['percentage'],
                    'agent_anc_nta_agent_total_amount': agent_data['ancillary']['nta_agent']['total']['amount'],
                    'agent_anc_nta_agent_upsell_percentage': agent_data['ancillary']['nta_agent']['upsell_by_percentage']['percentage'],
                    'agent_anc_nta_agent_upsell_minimum': agent_data['ancillary']['nta_agent']['upsell_by_percentage']['minimum'],
                    'agent_anc_nta_agent_upsell_has_minimum': agent_data['ancillary']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'agent_anc_nta_agent_upsell_maximum': agent_data['ancillary']['nta_agent']['upsell_by_percentage']['maximum'],
                    'agent_anc_nta_agent_upsell_has_maximum': agent_data['ancillary']['nta_agent']['upsell_by_percentage']['has_maximum'],
                    'agent_anc_nta_agent_upsell_amount': agent_data['ancillary']['nta_agent']['upsell_by_amount']['amount'],
                    'agent_rsv_nta_agent_upsell_amount': agent_data['reservation']['nta_agent']['upsell_by_amount']['amount'],
                    'agent_rsv_nta_agent_upsell_route': agent_data['reservation']['nta_agent']['upsell_by_amount']['is_route'],
                    'agent_rsv_nta_agent_upsell_segment': agent_data['reservation']['nta_agent']['upsell_by_amount']['is_segment'],
                    'agent_rsv_nta_agent_upsell_percentage': agent_data['reservation']['nta_agent']['upsell_by_percentage']['percentage'],
                    'agent_rsv_nta_agent_upsell_minimum': agent_data['reservation']['nta_agent']['upsell_by_percentage']['minimum'],
                    'agent_rsv_nta_agent_upsell_has_minimum': agent_data['reservation']['nta_agent']['upsell_by_percentage']['has_minimum'],
                    'agent_rsv_nta_agent_upsell_maximum': agent_data['reservation']['nta_agent']['upsell_by_percentage']['maximum'],
                    'agent_rsv_nta_agent_upsell_has_maximum': agent_data['reservation']['nta_agent']['upsell_by_percentage']['has_maximum'],
                })
                if agent_data['reservation'].get('commission'):
                    values.update({
                        'agent_rsv_com_tax_amount': agent_data['reservation']['commission'].get('tax_amount', ''),
                        'agent_rsv_com_tax_percentage': agent_data['reservation']['commission'].get('tax_percentage', ''),
                        'agent_rsv_com_rounding': agent_data['reservation']['commission'].get('rounding', ''),
                    })
                if agent_data['ticketing'].get('commission'):
                    values.update({
                        'agent_tkt_com_tax_amount': agent_data['ticketing']['commission'].get('tax_amount', ''),
                        'agent_tkt_com_tax_percentage': agent_data['ticketing']['commission'].get('tax_percentage', ''),
                        'agent_tkt_com_rounding': agent_data['ticketing']['commission'].get('rounding', ''),
                    })
                if agent_data['ancillary'].get('commission'):
                    values.update({
                        'agent_anc_com_tax_amount': agent_data['ancillary']['commission'].get('tax_amount', ''),
                        'agent_anc_com_tax_percentage': agent_data['ancillary']['commission'].get('tax_percentage', ''),
                        'agent_anc_com_rounding': agent_data['ancillary']['commission'].get('rounding', ''),
                    })
                if agent_data['reservation'].get('ho_commission'):
                    values.update({
                        'agent_rsv_ho_com_tax_amount': agent_data['reservation']['ho_commission'].get('tax_amount', ''),
                        'agent_rsv_ho_com_tax_percentage': agent_data['reservation']['ho_commission'].get('tax_percentage', ''),
                        'agent_rsv_ho_com_rounding': agent_data['reservation']['ho_commission'].get('rounding', ''),
                    })
                if agent_data['ticketing'].get('ho_commission'):
                    values.update({
                        'agent_tkt_ho_com_tax_amount': agent_data['ticketing']['ho_commission'].get('tax_amount', ''),
                        'agent_tkt_ho_com_tax_percentage': agent_data['ticketing']['ho_commission'].get('tax_percentage', ''),
                        'agent_tkt_ho_com_rounding': agent_data['ticketing']['ho_commission'].get('rounding', ''),
                    })
                if agent_data['ancillary'].get('ho_commission'):
                    values.update({
                        'agent_anc_ho_com_tax_amount': agent_data['ancillary']['ho_commission'].get('tax_amount', ''),
                        'agent_anc_ho_com_tax_percentage': agent_data['ancillary']['ho_commission'].get('tax_percentage', ''),
                        'agent_anc_ho_com_rounding': agent_data['ancillary']['ho_commission'].get('rounding', ''),
                    })

                if agent_data['route'].get('total', {}):
                    values.update({
                        'agent_total_type': agent_data['route']['total'].get('access_type', ''),
                        'agent_total_less_amount': agent_data['route']['total'].get('less_amount', ''),
                        'agent_total_is_less_equal': agent_data['route']['total'].get('is_less_equal', ''),
                        'agent_total_greater_amount': agent_data['route']['total'].get('greater_amount', ''),
                        'agent_total_is_greater_equal': agent_data['route']['total'].get('is_greater_equal', ''),
                    })

        if customer_data:
            cust_pricing_obj = self.env['tt.customer.pricing'].search([('id', '=', customer_data['pricing_id'])], limit=1)
            cust_pricing_line_obj = self.env['tt.customer.pricing.line'].search([('id', '=', customer_data['rule_id'])], limit=1)
            if cust_pricing_obj and cust_pricing_line_obj:
                values.update({
                    'customer_pricing_id': customer_data['pricing_id'],
                    'customer_pricing_sequence': customer_data['parent_data']['sequence'],
                    'customer_pricing_index': customer_data['pricing_index'],
                    'customer_parent_access_type': customer_data['parent_data']['customer_parent']['access_type'],
                    'customer_parent_id_list': customer_data['parent_data']['customer_parent']['customer_parent_id_list'],
                    'customer_parent_type_access_type': customer_data['parent_data']['customer_parent_type']['access_type'],
                    'customer_parent_type_code_list': customer_data['parent_data']['customer_parent_type']['customer_parent_type_code_list'],
                    'customer_provider_access_type': customer_data['parent_data']['provider']['access_type'],
                    'customer_provider_code_list': customer_data['parent_data']['provider']['provider_code_list'],
                    'customer_provider_type_access_type': customer_data['parent_data']['provider_type']['access_type'],
                    'customer_provider_type_code_list': customer_data['parent_data']['provider_type']['provider_type_code_list'],
                    'customer_carrier_access_type': customer_data['parent_data']['carrier']['access_type'],
                    'customer_carrier_code_list': customer_data['parent_data']['carrier']['carrier_code_list'],
                    'customer_pricing_line_id': customer_data['rule_id'],
                    'customer_pricing_line_sequence': customer_data['sequence'],
                    'customer_pricing_line_index': customer_data['rule_index'],
                    'customer_currency_code': customer_data.get('currency_code', ''),
                    'customer_set_expiration_date': customer_data['set_expiration_date'],
                    'customer_date_from': customer_data['date_from'] if customer_data['date_from'] else None,
                    'customer_date_to': customer_data['date_to'] if customer_data['date_to'] else None,
                    'customer_origin_access_type': customer_data['route']['origin']['access_type'],
                    'customer_origin_code_list': customer_data['route']['origin']['destination_code_list'],
                    'customer_origin_city_code_list': customer_data['route']['origin']['city_code_list'],
                    'customer_origin_country_code_list': customer_data['route']['origin']['country_code_list'],
                    'customer_destination_access_type': customer_data['route']['destination']['access_type'],
                    'customer_destination_code_list': customer_data['route']['destination']['destination_code_list'],
                    'customer_destination_city_code_list': customer_data['route']['destination']['city_code_list'],
                    'customer_destination_country_code_list': customer_data['route']['destination']['country_code_list'],
                    'customer_class_of_service_access_type': customer_data['route']['class_of_service']['access_type'],
                    'customer_class_of_service_list': customer_data['route']['class_of_service']['class_of_service_list'],
                    'customer_charge_code_access_type': customer_data['route']['charge_code']['access_type'],
                    'customer_charge_code_list': customer_data['route']['charge_code']['charge_code_list'],
                    'customer_tour_code_access_type': customer_data['route']['charge_code']['access_type'],
                    'customer_tour_code_list': customer_data['route']['charge_code']['charge_code_list'],
                    'customer_dot_access_type': customer_data['route']['date_of_travel']['access_type'] if customer_data['route'].get('date_of_travel') else '',
                    'customer_dot_start_date': customer_data['route']['date_of_travel']['start_date'] if customer_data['route'].get('date_of_travel') else '',
                    'customer_dot_end_date': customer_data['route']['date_of_travel']['end_date'] if customer_data['route'].get('date_of_travel') else '',
                    'customer_tkt_sales_upsell_percentage': customer_data['ticketing']['sales']['upsell_by_percentage']['percentage'],
                    'customer_tkt_sales_upsell_minimum': customer_data['ticketing']['sales']['upsell_by_percentage']['minimum'],
                    'customer_tkt_sales_upsell_has_minimum': customer_data['ticketing']['sales']['upsell_by_percentage']['has_minimum'],
                    'customer_tkt_sales_upsell_maximum': customer_data['ticketing']['sales']['upsell_by_percentage']['maximum'],
                    'customer_tkt_sales_upsell_has_maximum': customer_data['ticketing']['sales']['upsell_by_percentage']['has_maximum'],
                    'customer_tkt_sales_upsell_percentage_infant': customer_data['ticketing']['sales']['upsell_by_percentage']['is_infant'],
                    'customer_tkt_sales_upsell_amount': customer_data['ticketing']['sales']['upsell_by_amount']['amount'],
                    'customer_tkt_sales_upsell_route': customer_data['ticketing']['sales']['upsell_by_amount']['is_route'],
                    'customer_tkt_sales_upsell_segment': customer_data['ticketing']['sales']['upsell_by_amount']['is_segment'],
                    'customer_tkt_sales_upsell_amount_infant': customer_data['ticketing']['sales']['upsell_by_amount']['is_infant'],
                    'customer_anc_sales_upsell_percentage': customer_data['ancillary']['sales']['upsell_by_percentage']['percentage'],
                    'customer_anc_sales_upsell_minimum': customer_data['ancillary']['sales']['upsell_by_percentage']['minimum'],
                    'customer_anc_sales_upsell_has_minimum': customer_data['ancillary']['sales']['upsell_by_percentage']['has_minimum'],
                    'customer_anc_sales_upsell_maximum': customer_data['ancillary']['sales']['upsell_by_percentage']['maximum'],
                    'customer_anc_sales_upsell_has_maximum': customer_data['ancillary']['sales']['upsell_by_percentage']['has_maximum'],
                    'customer_anc_sales_upsell_amount': customer_data['ancillary']['sales']['upsell_by_amount']['amount'],
                    'customer_rsv_sales_upsell_amount': customer_data['reservation']['sales']['upsell_by_amount']['amount'],
                    'customer_rsv_sales_upsell_route': customer_data['reservation']['sales']['upsell_by_amount']['is_route'],
                    'customer_rsv_sales_upsell_segment': customer_data['reservation']['sales']['upsell_by_amount']['is_segment'],
                    'customer_rsv_sales_upsell_percentage': customer_data['reservation']['sales']['upsell_by_percentage']['percentage'],
                    'customer_rsv_sales_upsell_minimum': customer_data['reservation']['sales']['upsell_by_percentage']['minimum'],
                    'customer_rsv_sales_upsell_has_minimum': customer_data['reservation']['sales']['upsell_by_percentage']['has_minimum'],
                    'customer_rsv_sales_upsell_maximum': customer_data['reservation']['sales']['upsell_by_percentage']['maximum'],
                    'customer_rsv_sales_upsell_has_maximum': customer_data['reservation']['sales']['upsell_by_percentage']['has_maximum'],
                })
                if customer_data['reservation'].get('commission'):
                    values.update({
                        'customer_rsv_com_tax_amount': customer_data['reservation']['commission'].get('tax_amount', ''),
                        'customer_rsv_com_tax_percentage': customer_data['reservation']['commission'].get('tax_percentage', ''),
                        'customer_rsv_com_rounding': customer_data['reservation']['commission'].get('rounding', ''),
                    })
                if customer_data['ticketing'].get('commission'):
                    values.update({
                        'customer_tkt_com_tax_amount': customer_data['ticketing']['commission'].get('tax_amount', ''),
                        'customer_tkt_com_tax_percentage': customer_data['ticketing']['commission'].get('tax_percentage', ''),
                        'customer_tkt_com_rounding': customer_data['ticketing']['commission'].get('rounding', ''),
                    })
                if customer_data['ancillary'].get('commission'):
                    values.update({
                        'customer_anc_com_tax_amount': customer_data['ancillary']['commission'].get('tax_amount', ''),
                        'customer_anc_com_tax_percentage': customer_data['ancillary']['commission'].get('tax_percentage', ''),
                        'customer_anc_com_rounding': customer_data['ancillary']['commission'].get('rounding', ''),
                    })
                if customer_data['reservation'].get('ho_commission'):
                    values.update({
                        'customer_rsv_ho_com_tax_amount': customer_data['reservation']['ho_commission'].get('tax_amount', ''),
                        'customer_rsv_ho_com_tax_percentage': customer_data['reservation']['ho_commission'].get('tax_percentage', ''),
                        'customer_rsv_ho_com_rounding': customer_data['reservation']['ho_commission'].get('rounding', ''),
                    })
                if customer_data['ticketing'].get('ho_commission'):
                    values.update({
                        'customer_tkt_ho_com_tax_amount': customer_data['ticketing']['ho_commission'].get('tax_amount', ''),
                        'customer_tkt_ho_com_tax_percentage': customer_data['ticketing']['ho_commission'].get('tax_percentage', ''),
                        'customer_tkt_ho_com_rounding': customer_data['ticketing']['ho_commission'].get('rounding', ''),
                    })
                if customer_data['ancillary'].get('ho_commission'):
                    values.update({
                        'customer_anc_ho_com_tax_amount': customer_data['ancillary']['ho_commission'].get('tax_amount', ''),
                        'customer_anc_ho_com_tax_percentage': customer_data['ancillary']['ho_commission'].get('tax_percentage', ''),
                        'customer_anc_ho_com_rounding': customer_data['ancillary']['ho_commission'].get('rounding', ''),
                    })

                if customer_data['route'].get('total', {}):
                    values.update({
                        'customer_total_type': customer_data['route']['total'].get('access_type', ''),
                        'customer_total_less_amount': customer_data['route']['total'].get('less_amount', ''),
                        'customer_total_is_less_equal': customer_data['route']['total'].get('is_less_equal', ''),
                        'customer_total_greater_amount': customer_data['route']['total'].get('greater_amount', ''),
                        'customer_total_is_greater_equal': customer_data['route']['total'].get('is_greater_equal', ''),
                    })

        if agent_com_data:
            agentcom_pricing_obj = self.env['tt.agent.commission'].search([('id', '=', agent_com_data['pricing_id'])], limit=1)
            agentcom_pricing_line_obj = self.env['tt.agent.commission.line'].search([('id', '=', agent_com_data['rule_id'])], limit=1)
            if agentcom_pricing_obj and agentcom_pricing_line_obj:
                values.update({
                    'agent_commission_id': agent_com_data['pricing_id'],
                    'agent_commission_sequence': agent_com_data['parent_data']['sequence'],
                    'agent_commission_index': agent_com_data['pricing_index'],
                    'agent_commission_provider_access_type': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_provider_code_list': agent_com_data['parent_data']['provider']['provider_code_list'],
                    'agent_commission_provider_type_access_type': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_provider_type_code_list': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_carrier_access_type': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_carrier_code_list': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_access_type': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_id_list': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_type_access_type': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_type_code_list': agent_com_data['parent_data']['provider']['access_type'],
                    'agent_commission_line_id': agent_com_data['rule_id'],
                    'agent_commission_line_sequence': agent_com_data['sequence'],
                    'agent_commission_line_index': agent_com_data['rule_index'],
                    'agent_commission_currency_code': agent_com_data.get('currency_code', ''),
                    'agent_commission_set_expiration_date': agent_com_data['set_expiration_date'],
                    'agent_commission_date_from': agent_com_data['date_from'] if agent_com_data['date_from'] else None,
                    'agent_commission_date_to': agent_com_data['date_to'] if agent_com_data['date_to'] else None,
                    'agent_commission_origin_access_type': agent_com_data['route']['origin']['access_type'],
                    'agent_commission_origin_code_list': agent_com_data['route']['origin']['destination_code_list'],
                    'agent_commission_origin_city_code_list': agent_com_data['route']['origin']['city_code_list'],
                    'agent_commission_origin_country_code_list': agent_com_data['route']['origin']['country_code_list'],
                    'agent_commission_destination_access_type': agent_com_data['route']['destination']['access_type'],
                    'agent_commission_destination_code_list': agent_com_data['route']['destination']['destination_code_list'],
                    'agent_commission_destination_city_code_list': agent_com_data['route']['destination']['city_code_list'],
                    'agent_commission_destination_country_code_list': agent_com_data['route']['destination']['country_code_list'],
                    'agent_commission_class_of_service_access_type': agent_com_data['route']['class_of_service']['access_type'],
                    'agent_commission_class_of_service_list': agent_com_data['route']['class_of_service']['class_of_service_list'],
                    'agent_commission_charge_code_access_type': agent_com_data['route']['charge_code']['access_type'],
                    'agent_commission_charge_code_list': agent_com_data['route']['charge_code']['charge_code_list'],
                    'agent_commission_tour_code_access_type': agent_com_data['route']['charge_code']['access_type'],
                    'agent_commission_tour_code_list': agent_com_data['route']['charge_code']['charge_code_list'],
                    'agent_commission_dot_access_type': agent_com_data['route']['date_of_travel']['access_type'] if agent_com_data['route'].get('date_of_travel') else '',
                    'agent_commission_dot_start_date': agent_com_data['route']['date_of_travel']['start_date'] if agent_com_data['route'].get('date_of_travel') else '',
                    'agent_commission_dot_end_date': agent_com_data['route']['date_of_travel']['end_date'] if agent_com_data['route'].get('date_of_travel') else '',
                    'agent_commission_parent_charge_percentage': agent_com_data['commission']['parent']['charge_by_percentage']['percentage'],
                    'agent_commission_parent_charge_minimum': agent_com_data['commission']['parent']['charge_by_percentage']['minimum'],
                    'agent_commission_parent_charge_has_minimum': agent_com_data['commission']['parent']['charge_by_percentage']['has_minimum'],
                    'agent_commission_parent_charge_maximum': agent_com_data['commission']['parent']['charge_by_percentage']['maximum'],
                    'agent_commission_parent_charge_has_maximum': agent_com_data['commission']['parent']['charge_by_percentage']['has_maximum'],
                    'agent_commission_parent_charge_amount': agent_com_data['commission']['parent']['charge_by_amount']['amount'],
                    'agent_commission_parent_charge_route': agent_com_data['commission']['parent']['charge_by_amount']['is_route'],
                    'agent_commission_parent_charge_segment': agent_com_data['commission']['parent']['charge_by_amount']['is_segment'],
                    'agent_commission_parent_charge_pax': agent_com_data['commission']['parent']['charge_by_amount']['is_pax'],
                    'agent_commission_parent_charge_infant': agent_com_data['commission']['parent']['charge_by_amount']['is_infant'],
                    'agent_commission_ho_charge_percentage': agent_com_data['commission']['ho']['charge_by_percentage']['percentage'],
                    'agent_commission_ho_charge_minimum': agent_com_data['commission']['ho']['charge_by_percentage']['minimum'],
                    'agent_commission_ho_charge_has_minimum': agent_com_data['commission']['ho']['charge_by_percentage']['has_minimum'],
                    'agent_commission_ho_charge_maximum': agent_com_data['commission']['ho']['charge_by_percentage']['maximum'],
                    'agent_commission_ho_charge_has_maximum': agent_com_data['commission']['ho']['charge_by_percentage']['has_maximum'],
                    'agent_commission_ho_charge_amount': agent_com_data['commission']['ho']['charge_by_amount']['amount'],
                    'agent_commission_ho_charge_route': agent_com_data['commission']['ho']['charge_by_amount']['is_route'],
                    'agent_commission_ho_charge_segment': agent_com_data['commission']['ho']['charge_by_amount']['is_segment'],
                    'agent_commission_ho_charge_pax': agent_com_data['commission']['ho']['charge_by_amount']['is_pax'],
                    'agent_commission_ho_charge_infant': agent_com_data['commission']['ho']['charge_by_amount']['is_infant'],
                    'agent_commission_commission_percentage': agent_com_data['commission']['agent']['commission_by_percentage']['percentage'],
                    'agent_commission_commission_minimum': agent_com_data['commission']['agent']['commission_by_percentage']['minimum'],
                    'agent_commission_commission_has_minimum': agent_com_data['commission']['agent']['commission_by_percentage']['has_minimum'],
                    'agent_commission_commission_maximum': agent_com_data['commission']['agent']['commission_by_percentage']['maximum'],
                    'agent_commission_commission_has_maximum': agent_com_data['commission']['agent']['commission_by_percentage']['has_maximum'],
                    'agent_commission_commission_amount': agent_com_data['commission']['agent']['commission_by_amount']['amount'],
                    'agent_commission_commission_route': agent_com_data['commission']['agent']['commission_by_amount']['is_route'],
                    'agent_commission_commission_segment': agent_com_data['commission']['agent']['commission_by_amount']['is_segment'],
                    'agent_commission_commission_pax': agent_com_data['commission']['agent']['commission_by_amount']['is_pax'],
                    'agent_commission_commission_infant': agent_com_data['commission']['agent']['commission_by_amount']['is_infant'],
                    'agent_commission_residual_amount_to': agent_com_data['commission']['residual_amount_to'],
                    'agent_commission_discount_percentage': agent_com_data['commission']['agent']['discount_by_percentage']['percentage'],
                    'agent_commission_discount_minimum': agent_com_data['commission']['agent']['discount_by_percentage']['minimum'],
                    'agent_commission_discount_has_minimum': agent_com_data['commission']['agent']['discount_by_percentage']['has_minimum'],
                    'agent_commission_discount_maximum': agent_com_data['commission']['agent']['discount_by_percentage']['maximum'],
                    'agent_commission_discount_has_maximum': agent_com_data['commission']['agent']['discount_by_percentage']['has_maximum'],
                    'agent_commission_discount_amount': agent_com_data['commission']['agent']['discount_by_amount']['amount'],
                    'agent_commission_discount_route': agent_com_data['commission']['agent']['discount_by_amount']['is_route'],
                    'agent_commission_discount_segment': agent_com_data['commission']['agent']['discount_by_amount']['is_segment'],
                    'agent_commission_discount_pax': agent_com_data['commission']['agent']['discount_by_amount']['is_pax'],
                    'agent_commission_discount_infant': agent_com_data['commission']['agent']['discount_by_amount']['is_infant'],
                })
                if agent_com_data['route'].get('total', {}):
                    values.update({
                        'agent_commission_total_type': agent_com_data['route']['total'].get('access_type', ''),
                        'agent_commission_total_less_amount': agent_com_data['route']['total'].get('less_amount', ''),
                        'agent_commission_total_is_less_equal': agent_com_data['route']['total'].get('is_less_equal', ''),
                        'agent_commission_total_greater_amount': agent_com_data['route']['total'].get('greater_amount', ''),
                        'agent_commission_total_is_greater_equal': agent_com_data['route']['total'].get('is_greater_equal', ''),
                    })

        self.write(values)
        _logger.info('Compute Raw Data : DONE')

    def to_dict(self):
        provider_pricing_data = {}
        if self.provider_pricing_line_id:
            pricing_id = self.provider_pricing_id.id if self.provider_pricing_id else ''
            provider_pricing_data = {
                "less": {
                    'percentage': float(self.provider_less_percentage) if self.provider_less_percentage else 0.0,
                    'is_infant': True if self.provider_less_infant == 'True' else False,
                    'tour_code': self.provider_less_tour_code if self.provider_less_tour_code else '',
                },
                "pricing_id": pricing_id,
                "rule_id": self.provider_pricing_line_id.id,
            }

        agent_pricing_data = {}
        if self.agent_pricing_line_id:
            agent_pricing_data = {
                "pricing_id": self.agent_pricing_id.id if self.agent_pricing_id else '',
                "rule_id": self.agent_pricing_line_id.id,
            }

        customer_pricing_data = {}
        if self.customer_pricing_line_id:
            customer_pricing_data = {
                "pricing_id": self.customer_pricing_id.id if self.customer_pricing_id else '',
                "rule_id": self.customer_pricing_line_id.id,
            }

        agent_commission_data = {}
        if self.agent_commission_line_id:
            agent_commission_data = {
                "pricing_id": self.agent_commission_id.id if self.agent_commission_id else '',
                "rule_id": self.agent_commission_line_id.id,
            }

        result = {
            "provider_pricing_data": provider_pricing_data,
            "agent_pricing_data": agent_pricing_data,
            "customer_pricing_data": customer_pricing_data,
            "agent_commission_data": agent_commission_data
        }
        return result


class TtProviderAirlinePricingUpline(models.Model):
    _name = 'tt.provider.airline.pricing.upline'
    _description = 'Provider Airline Pricing Upline'

    pricing_id = fields.Many2one('tt.provider.airline.pricing', 'Pricing', ondelete='cascade')
    sequence = fields.Char('Sequence', readonly=1)
    index = fields.Char('Index', readonly=1)
    agent_type_code = fields.Char('Agent Type Code', readonly=1)
    pricing_type = fields.Selection([
        ('', ''),
        ('agent', 'Agent'),
        ('agent_commission', 'Agent Commission'),
    ], 'Pricing Type', default='', readonly=1)
    commission_percentage = fields.Char('Commission (%)', readonly=1)
    commission_minimum = fields.Char('Commission Minimum', readonly=1)
    commission_has_minimum = fields.Char('Has Minimum', readonly=1)
    commission_maximum = fields.Char('Commission Maximum', readonly=1)
    commission_has_maximum = fields.Char('Has Maximum', readonly=1)
    commission_amount = fields.Char('Commission Amount', readonly=1)
    commission_route = fields.Char('Commission Route', readonly=1)
    commission_segment = fields.Char('Commission Segment', readonly=1)
    commission_pax = fields.Char('Commission Pax', readonly=1)
    commission_infant = fields.Char('Commission Include Infant', readonly=1)
