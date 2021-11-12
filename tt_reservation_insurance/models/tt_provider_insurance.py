from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
import json, logging
from ...tools.db_connector import GatewayConnector
import traceback


_logger = logging.getLogger(__name__)


class TtProviderInsurance(models.Model):
    _name = 'tt.provider.insurance'
    _inherit = 'tt.history'
    _rec_name = 'pnr'
    _order = 'start_date'
    _description = 'Provider Insurance'

    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    pnr2 = fields.Char('PNR2', readonly=True, states={'draft': [('readonly', False)]})
    provider_id = fields.Many2one('tt.provider','Provider', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft', readonly=True, states={'draft': [('readonly', False)]})
    booking_id = fields.Many2one('tt.reservation.insurance', 'Order Number', ondelete='cascade', readonly=True, states={'draft': [('readonly', False)]})
    sequence = fields.Integer('Sequence', readonly=True, states={'draft': [('readonly', False)]})
    balance_due = fields.Float('Balance Due', default=0, readonly=True, states={'draft': [('readonly', False)]})
    origin = fields.Char('Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination = fields.Char('Destination', readonly=True, states={'draft': [('readonly', False)]})
    start_date = fields.Char('Start Date', readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Char('End Date', readonly=True, states={'draft': [('readonly', False)]})
    master_trip = fields.Selection([('1', 'Single Trip (Tunggal)'), ('2', 'Annual (Tahunan)')], 'Master Trip', readonly=True, states={'draft': [('readonly', False)]})
    master_area = fields.Selection([('1', 'Asia Pacific (Asia Pasifik)'), ('2', 'World Wide (Seluruh Dunia)'),
                                    ('3', 'Schengen Countries (Negara Schengen)'), ('4', 'Domestic (Domestik)')], 'Master Area', readonly=True, states={'draft': [('readonly', False)]})
    plan_trip = fields.Selection([('1', 'DINAS'), ('2', 'LAINNYA'), ('3', 'WISATA')], 'Plan Trip', readonly=True, states={'draft': [('readonly', False)]})
    carrier_id = fields.Many2one('tt.transport.carrier', 'Product')
    carrier_code = fields.Char('Product Code')
    carrier_name = fields.Char('Product Name')
    product_type = fields.Selection([('1', 'Individual'), ('2', 'Family')], 'Product Type', readonly=True, states={'draft': [('readonly', False)]}, compute='compute_product_type', store=True)
    sid_issued = fields.Char('SID Issued', readonly=True, states={'draft': [('readonly', False)]})#signature generate sendiri
    sid_cancel = fields.Char('SID Cancel', readonly=True, states={'draft': [('readonly', False)]})#signature generate sendiri
    total_price = fields.Float('Total Price', default=0, readonly=True, states={'draft': [('readonly', False)]})
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_insurance_booking_id', 'Cost Service Charges', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    additional_vendor_pricing_info = fields.Text('Additional Vendor Pricing Info', readonly=True)
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

    ticket_ids = fields.One2many('tt.ticket.insurance', 'provider_id', 'Ticket Number', readonly=True, states={'draft': [('readonly', False)]})

    error_history_ids = fields.One2many('tt.reservation.err.history','res_id','Error History', domain=[('res_model','=','tt.provider.insurance')], readonly=True, states={'draft': [('readonly', False)]})

    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled', readonly=True, states={'draft': [('readonly', False)]})
    reconcile_time = fields.Datetime('Reconcile Time', readonly=True, states={'draft': [('readonly', False)]})

    @api.depends('carrier_id')
    @api.onchange('carrier_id')
    def compute_product_type(self):
        if self.carrier_id.code in ['1', '2', '3', '4', '8', '9']:
            self.product_type = '1'
        elif self.carrier_id.code in ['5', '6', '7']:
            self.product_type = '2'
        else:
            self.product_type = False

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
        payment_res = self.booking_id.payment_reservation_api('insurance',req,context)
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
        for key in ['pnr', 'pnr2', 'reference', 'balance_due', 'balance_due_str', 'total_price', 'penalty_amount', 'penalty_currency']:
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
    def action_booked_api_insurance(self, provider_data, api_context):
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

    # def action_booked_api_insurance(self, api_context):
    #     for rec in self:
    #         rec.write({
    #             'state': 'booked',
    #             'booked_uid': api_context['co_uid'],
    #             'booked_date': fields.Datetime.now(),
    #         })

    def action_booked_pending_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'booked_pending',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })

    def action_void_pending_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'void_pending',
                'cancel_uid': api_context['co_uid'],
                'cancel_date': fields.Datetime.now(),
            })

    def action_void_api_insurance(self, provider_data, api_context):
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

    def action_issued_pending_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'issued_pending',
                'issued_uid': api_context['co_uid'],
                'issued_date': fields.Datetime.now(),
            })

    def action_refund_api_insurance(self, provider_data, api_context):
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

    def action_rescheduled_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'rescheduled',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_reissue_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'reissue',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_rescheduled_pending_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'rescheduled_pending',
                'rescheduled_uid': api_context['co_uid'],
                'rescheduled_date': fields.Datetime.now(),
            })

    def action_halt_booked_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'halt_booked',
                'hold_date': datetime.now() + timedelta(minutes=30)
            })

    def action_halt_issued_api_insurance(self, api_context):
        for rec in self:
            rec.write({
                'state': 'halt_issued',
                'hold_date': datetime.now() + timedelta(minutes=30)
            })

    def action_failed_void_api_insurance(self,err_code,err_msg):
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

    def action_refund_failed_api_insurance(self,err_code,err_msg):
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

    def action_failed_rescheduled_api_insurance(self,err_code,err_msg):
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
    # def action_issued_api_insurance(self,context):
    def action_issued_api_insurance(self, provider_data, context):
        for rec in self:
            values = {
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
                'balance_due': 0
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

    def action_cancel_api_insurance(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_refund_pending_api_insurance(self,context):
        for rec in self:
            rec.write({
                'state': 'refund_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_cancel_pending_api_insurance(self,context):
        for rec in self:
            rec.write({
                'state': 'cancel_pending',
                'cancel_date': datetime.now(),
                'cancel_uid': context['co_uid'],
                'sid_cancel': context['signature'],
            })

    def action_failed_booked_api_insurance(self,err_code,err_msg):
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

    def action_failed_issued_api_insurance(self,err_code,err_msg):
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

    def update_ticket_api(self, passengers):  ##isi ticket number
        ticket_not_found = []
        for psg in passengers:
            ticket_found = False
            for ticket in self.ticket_ids:
                psg_name = ticket.passenger_id.name.replace(' ', '').lower()
                if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ', '').lower() in [psg_name,
                                                                                                 psg_name * 2] and not ticket.ticket_number:
                    ticket.write({
                        'ticket_number': psg.get('ticket_number', '')
                    })
                    ticket_found = True
                    ticket.passenger_id.is_ticketed = True
                    break
            if not ticket_found:
                ticket_not_found.append(psg)

        for psg in ticket_not_found:
            self.write({
                'ticket_ids': [(0, 0, {
                    'ticket_number': psg.get('ticket_number'),
                    'pax_type': psg.get('pax_type'),
                })]
            })

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            currency_id = currency_obj.get_id(scs.get('currency'),default_param_idr=True)
            foreign_currency_id = currency_obj.get_id(scs.get('foreign_currency'),default_param_idr=True)
            scs_pax_count = 0
            total = 0
            passenger_insurance_ids = []
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type and scs_pax_count < scs['pax_count']:
                    passenger_insurance_ids.append(psg.passenger_id.id)
                    # scs['pax_count'] += 1
                    scs_pax_count += 1
                    total += scs['amount']
            scs.update({
                'passenger_insurance_ids': [(6, 0, passenger_insurance_ids)],
                'total': total,
                'currency_id': currency_id,
                'foreign_currency_id': foreign_currency_id,
                'provider_insurance_booking_id': self.id,
                'description': self.pnr and self.pnr or str(self.sequence),
            })
            scs.pop('currency')
            scs.pop('foreign_currency')
            # END
            service_chg_obj.create(scs)

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
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'balance_due': self.balance_due,
            'total_price': self.total_price,
            'origin': self.origin,
            'destination': self.destination,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'carrier_code': self.carrier_id.code,
            'carrier_name': self.carrier_id.name,
            'master_area': self.master_area,
            'master_area_str': dict(self._fields['master_area'].selection).get(self.master_area),
            'plan_trip': self.plan_trip,
            'plan_trip_str': dict(self._fields['plan_trip'].selection).get(self.plan_trip),
            'master_trip': self.master_trip,
            'master_trip_str': dict(self._fields['master_trip'].selection).get(self.master_trip),
            'product_type': self.product_type,
            'product_type_str': dict(self._fields['product_type'].selection).get(self.product_type),
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
            'additional_vendor_pricing_info': self.additional_vendor_pricing_info and json.loads(self.additional_vendor_pricing_info) or {},
            'error_msg': self.error_history_ids and self.error_history_ids[-1].error_msg or ''
        }

        return res

    def get_carrier_name(self):
        carrier_names = set([])
        for journey in self.journey_ids:
            for segment in journey.segment_ids:
                if segment.carrier_id:
                    carrier_names.add(segment.carrier_id.name)
        return carrier_names
