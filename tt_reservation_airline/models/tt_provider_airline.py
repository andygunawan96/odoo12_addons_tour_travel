from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
import json, logging
from ...tools.db_connector import GatewayConnector
import traceback


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
    hold_date = fields.Char('Hold Date', readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True, states={'draft': [('readonly', False)]})
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
    total_price = fields.Float('Total Price', default=0, readonly=True, states={'draft': [('readonly', False)]})
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

    ##button function
    def action_change_is_hold_date_sync(self):
        self.write({
            'is_hold_date_sync': not self.is_hold_date_sync
        })

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
            'provider': self.provider_id.code
        }
        res = self.env['tt.airline.api.con'].send_sync_refund_status(req)
        if res['error_code'] != 0:
            return False
        if res['response']['status'] == 'CANCELLED':
            self.write({
                'state': 'cancel',
                'cancel_date': datetime.now()
            })
            self.booking_id.check_provider_state({'co_uid': self.cancel_uid.id})

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

    def action_set_to_book_from_button(self):
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
        for key in ['pnr', 'pnr2', 'reference', 'balance_due', 'balance_due_str', 'total_price', 'penalty_amount', 'penalty_currency', 'is_hold_date_sync']:
            # if not provider_data.get(key):
            # todo ini buat ngecek klo key nya ada baru di update value nya
            if key not in provider_data_keys:
                continue
            values[key] = provider_data[key]
            # todo ini buat update data info pnr di ledger sama service charges (sblm booking itu sequence isi nya)
            if key == 'pnr':
                pnr = provider_data[key]
                provider_sequence = str(self.sequence)
                for sc in self.cost_service_charge_ids:
                    # todo ini kalau misal ternyata infonya uda pnr di skip, kalau belum di update
                    if sc.description != provider_data[key]:
                        sc.write({'description': pnr})

                for ledger in self.booking_id.ledger_ids:
                    # todo ini kalau misal ternyata infonya uda pnr di skip, kalau belum di update
                    if ledger.pnr == provider_sequence:
                        ledger.write({'pnr': pnr})

        if provider_data.get('hold_date'):
            values['hold_date'] = datetime.strptime(provider_data['hold_date'], "%Y-%m-%d %H:%M:%S")

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

    def action_halt_booked_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'halt_booked',
                'hold_date': datetime.now() + timedelta(minutes=30)
            })

    def action_halt_issued_api_airline(self, api_context):
        for rec in self:
            rec.write({
                'state': 'halt_issued',
                'hold_date': datetime.now() + timedelta(minutes=30)
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
        self.cancel_date = fields.Datetime.now()
        self.cancel_uid = self.env.user.id
        self.state = 'cancel'

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_ticket_api(self,passengers,pnr=""):
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

            if psg_obj:
                _logger.info(json.dumps(psg_obj.ids))
                if len(psg_obj.ids) > 1:
                    for psg_o in psg_obj:
                        if not psg_o.is_ticketed:
                            psg_obj = psg_o
                            break

                _logger.info(str(psg_obj))
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': psg.get('ticket_number'),
                    'passenger_id': psg_obj.id
                }))
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
            if idx >= len(psg_with_no_ticket):
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': psg.get('ticket_number'),
                }))
            else:
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': psg.get('ticket_number'),
                    'passenger_id': psg_with_no_ticket[idx].id
                }))
                psg_with_no_ticket[idx].is_ticketed = True
                psg_with_no_ticket[idx].create_ssr(psg['fees'],pnr,self.id)

        self.write({
            'ticket_ids': ticket_list
        })

    def update_ticket_api(self,passengers):##isi ticket number
        ticket_not_found = []
        for psg in passengers:
            ticket_found = False
            for ticket in self.ticket_ids:
                ticket_passenger_name = ticket.passenger_id and ticket.passenger_id.name or ''
                psg_name = ticket_passenger_name.replace(' ','').lower()
                if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ','').lower() in [psg_name, psg_name*2] and not ticket.ticket_number or (psg.get('ticket_number') and ticket.ticket_number == psg.get('ticket_number')):
                    ticket_values = {
                        'ticket_number': psg.get('ticket_number', ''),
                        'ff_number': psg.get('ff_number', ''),
                    }
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
        pnr_text = self.pnr if self.pnr else str(self.sequence)
        for psg in self.booking_id.passenger_ids:
            # June 30, 2021 - SAM
            # unlink dengan metode update One2many
            fee_id_list = []
            for fee in psg.fee_ids:
                # if fee.pnr != pnr_text:
                if fee.provider_id and fee.provider_id.id != self.id:
                    fee_id_list.append((4, fee.id))
                    continue
                # fee.unlink()
                fee_id_list.append((2, fee.id))
            psg.write({
                'fee_ids': fee_id_list
            })

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

    def action_create_ledger(self,issued_uid,pay_method=None):
        return self.env['tt.ledger'].action_create_ledger(self,issued_uid)
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
            'destination': self.destination_id.code,
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
            'penalty_amount': self.penalty_amount,
            'penalty_currency': self.penalty_currency and self.penalty_currency or '',
            'is_force_issued': self.booking_id.is_force_issued,
            'is_halt_process': self.booking_id.is_halt_process,
            # END
            # June 28, 2021 - SAM
            'rules': rules,
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
        if not self.provider_id:
            raise Exception('Provider is not set')
        req = {
            "provider": self.provider_id.code,
            "pnr": self.pnr,
            "pnr2": self.pnr2,
            "reference": self.reference
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
                GatewayConnector().telegram_notif_api(data, {})
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
            GatewayConnector().telegram_notif_api(data, {})
        except:
            _logger.error('Action reprice provider, error notif telegram, %s, %s' % (self.pnr, traceback.format_exc()))

        return True
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
