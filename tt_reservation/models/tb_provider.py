from odoo import api, fields, models, _
from .tt_reservation import BOOKING_STATE, JOURNEY_DIRECTION
from odoo.exceptions import UserError
from datetime import datetime
# from ...tools.ERR import RequestException

import logging
_logger = logging.getLogger(__name__)

from .ApiConnector_Airlines import ApiConnector_Airlines
API_CN_AIRLINES = ApiConnector_Airlines()


class TransportBookingProvider(models.Model):
    _name = 'tt.tb.provider'
    _rec_name = 'pnr'
    # _order = 'sequence'
    _order = 'departure_date'

    sequence = fields.Integer('Sequence')
    booking_id = fields.Many2one('tt.reservation', 'Order Number', ondelete='cascade')
    pnr = fields.Char('PNR')
    provider = fields.Char('Provider')
    state = fields.Selection(BOOKING_STATE, 'Status', default='draft')

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')

    ticket_ids = fields.One2many('tt.tb.ticket', 'tb_provider_id', 'Ticket Number')
    # cost_service_charge_ids = fields.One2many('tt.service.charge', 'tb_provider_id', 'Cost Service Charges')

    # direction = fields.Selection(JOURNEY_DIRECTION, string='Direction')
    # origin_id = fields.Many2one('tt.destinations', 'Origin')
    # destination_id = fields.Many2one('tt.destinations', 'Destination')
    # departure_date = fields.Datetime('Departure Date')
    # return_date = fields.Datetime('Return Date')
    # origin = fields.Char('Origin')
    # destination = fields.Char('Destination')
    #
    # journey_ids = fields.One2many('tt.tb.journey', 'provider_booking_id', string='Journeys')
    #
    # currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
    #                               default=lambda self: self.env.user.company_id.currency_id)
    # total = fields.Monetary(string='Total', readonly=True)
    # total_fare = fields.Monetary(string='Total Fare', compute="_compute_provider_total_fare", readonly=True)
    # total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    # promotion_code = fields.Char(string='Promotion Code')
    #
    # sid_connector = fields.Char('SID Connector', readonly=True)
    # sid = fields.Char('Session ID', readonly=True)
    #
    # # Booking Progress
    #
    # refund_uid = fields.Many2one('res.users', 'Refund By')
    # refund_date = fields.Datetime('Refund Date')
    #
    #

    #
    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})
    #

    def action_set_as_draft(self):
        self.write({
            'state': 'draft',
        })
        self.booking_id.message_post(body=_("PNR set as DRAFT: {} (Provider : {})".format(self.pnr, self.provider)))

    def action_set_as_booked(self):
        self.write({
            'state': 'booked',
        })
        self.booking_id.action_check_provider_state()
        self.booking_id.message_post(body=_("PNR set as BOOKED: {} (Provider : {})".format(self.pnr, self.provider)))

    def action_set_as_issued(self):
        self.write({
            'state': 'issued',
            'issued_uid': self.env.user.id
        })
        self.booking_id.action_check_provider_state()
        self.booking_id.message_post(body=_("PNR set as ISSUED: {} (Provider : {})".format(self.pnr, self.provider)))

    @api.depends('cost_service_charge_ids.pax_count', 'cost_service_charge_ids.amount')
    def _compute_provider_total_fare(self):
        total = 0
        for rec in self.cost_service_charge_ids:
            if rec.charge_code == 'fare':
                total += rec.total
        self.total_fare = total

    @api.depends('cost_service_charge_ids.pax_count', 'cost_service_charge_ids.amount')
    def _compute_provider_total(self):
        total = 0
        for rec in self.cost_service_charge_ids:
            total += rec.total
        self.total = total

    @api.depends('cost_service_charge_ids')
    def _compute_total(self):
        for rec in self:
            total = 0
            total_orig = 0
            for sc in rec.cost_service_charge_ids:
                if sc.charge_code.find('r.ac') < 0:
                    total += sc.total
                # total_orig adalah NTA
                total_orig += sc.total
            rec.write({
                'total': total,
                'total_orig': total_orig
            })

    def action_booked(self, pnr, api_context):
        for rec in self:
            rec.write({
                'pnr': pnr,
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
        self.env.cr.commit()

    def _validate_issued(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise UserError('User NOT FOUND...')
        if user_obj.agent_id.agent_type_id.id == self.env.ref('tt_base_rodex.agent_type_ho').id:
            raise UserError('User HO cannot Issuing...')
        return True

    def action_issued(self, api_context=None):
        if not api_context: #Jika dari Backend, TIDAK ada api_context
            api_context = {
                'co_uid': self.env.user.id,
            }
        # self._validate_issued(api_context=api_context)
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_uid': api_context['co_uid'],
                'issued_date': fields.Datetime.now(),
            })
            rec.booking_id.action_check_provider_state(api_context)

    def action_fail_issued(self, error_msg, api_context=None):
        if not api_context: #Jika dari Backend, TIDAK ada api_context
            api_context = {
                'co_uid': self.env.user.id,
            }
        for rec in self:
            if rec.state != 'issued':
                rec.write({
                    'state': 'fail_issue',
                    'issued_uid': api_context['co_uid'],
                    'issued_date': fields.Datetime.now(),
                    'error_msg': error_msg
                })
                rec.booking_id.action_check_provider_state(api_context)

    #############################################################################

    ## REMOVED by Samvi 2018/07/31
    def action_force_issued_api(self, api_context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_uid': api_context['co_uid'],
                'issued_date': fields.Datetime.now(),
            })

    ## REMOVED by Samvi 2018/07/31
    def action_force_issued(self, api_context=None):
        if not api_context: #Jika dari Backend, TIDAK ada api_context
            api_context = {
                'co_uid': self.env.user.id,
            }
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if user_obj.agent_id.agent_type_id.id != self.env.ref('tt_base_rodex.agent_type_ho').id:
            raise UserError('Only User HO can Issued...')

        self.action_force_issued_api(api_context)

    ##############################################################################

    # ## CREATED by Samvi 2018/07/31
    def action_force_issued(self):
        # This Function call for BUTTON issued on Backend
        api_context = {
            'co_uid': self.env.user.id
        }

        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if user_obj.agent_id.agent_type_id.id != self.env.ref('tt_base_rodex.agent_type_ho').id:
            raise UserError('Only User HO can Force Issued...')
        if not self.state == 'booked':
            raise UserError('State Is not Booked')
        if self.total > self.booking_id.agent_id.balance_actual:
            raise UserError(_('Not Enough Balance.'))

        self.action_create_ledger()
        self.action_issued(api_context)

        self.booking_id.message_post(body=_("PNR Force Issued: {} (Provider : {})".format(self.pnr, self.provider)))


    # ## CREATED by Samvi 2018/10/02
    def action_force_issued_provider_api(self, provider_id, api_context):
        # This Function use for Order Issued - API Client
        provider_obj = self.browse(provider_id)
        if not provider_obj.state == 'booked':
            raise UserError('State Is not Booked')
        if provider_obj.total > provider_obj.booking_id.agent_id.balance_actual:
            raise UserError(_('Not Enough Balance.'))

        provider_obj.action_create_ledger()
        provider_obj.action_issued(api_context)

        provider_obj.booking_id.message_post(body=_("PNR Force Issued: {} (Provider : {})".format(self.pnr, self.provider)))

    @api.one
    def _create_service_charge(self, service_charge_summary):
        if not service_charge_summary:
            pass
        for rec in self.cost_service_charge_ids:
            if rec.charge_type != 'VOUCHER':
                rec.sudo().unlink()
        # self.cost_service_charge_ids.sudo().unlink()
        service_chg_obj = self.env['tt.tb.service.charge']
        # Update Service Charge - Provider
        for scs in service_charge_summary:
            for val in scs['service_charges']:
                if val['amount']:
                    val['provider_booking_id'] = self.id
                    service_chg_obj.create(val)
            self._compute_total()

    @api.one
    def create_ticket_number(self, passenger_ids):
        # Variable name adalah first_name + last_name yang disambung semua tanpa spasi
        # Case nya bisa first_name = Budi Satria last_name Gunawan
        # atau first_name = Budi last_name Satria Gunawan
        passenger_list = []
        for rec in self.booking_id.passenger_ids:
            value = {
                'id': rec.id,
                'name': '{}{}'.format(''.join(rec.first_name.split(' ')).lower(), ''.join(rec.last_name.split(' ')).lower()),
            }
            passenger_list.append(value)

        for psg_data in passenger_ids:
            psg_data['name'] = '{}{}'.format(''.join(psg_data['first_name'].split(' ')).lower(), ''.join(psg_data['last_name'].split(' ')).lower())
            for psg_list in passenger_list:
                if not psg_list.get('ticket_number', False) and psg_list['name'] == psg_data['name']:
                    psg_list['ticket_number'] = psg_data.pop('ticket_number')
                    break

        self.ticket_ids.unlink()

        [self.ticket_ids.create({
            'passenger_id': rec['id'],
            'provider_id': self.id,
            'ticket_number': rec['ticket_number']
        }) for rec in passenger_list]

    def create_ledger(self):
        # ## UPDATED by Samvi 2018/07/24
        # ## Terdetect sebagai administrator jika sudo
        ledger_env = self.env['tt.ledger'].sudo()
        # ledger_env = self.env['tt.ledger']
        amount = 0
        for sc in self.cost_service_charge_ids:
            if sc.charge_code.find('r.ac') < 0:
                amount += sc.total
        booking_obj = self.booking_id
        ledger_values = ledger_env.prepare_vals('Order : ' + booking_obj.name, booking_obj.name,
                                                datetime.now(), 'transport', booking_obj.currency_id.id,
                                                0, amount)
        ledger_values.update({
            'transport_booking_id': booking_obj.id,
            'agent_id': booking_obj.agent_id.id,
            'pnr': self.pnr,
            'transport_type': booking_obj.transport_type,
            'display_provider_name': booking_obj.display_provider_name,
            'description': 'Provider : {}'.format(self.provider),
        })
        new_aml = ledger_env.create(ledger_values)
        new_aml.action_done()

    def create_commission_ledger(self):
        # ## UPDATED by Samvi 2018/07/24
        # ## Terdetect sebagai administrator jika sudo
        ledger_env = self.env['tt.ledger'].sudo()
        # ledger_env = self.env['tt.ledger']
        booking_obj = self.booking_id

        agent_commission = {}
        for sc in self.cost_service_charge_ids:
            # Pada lionair ada r.ac positif
            if 'r.ac' in sc.charge_code and sc.total < 0:
                amount = abs(sc.total)
                agent_id = sc['commision_agent_id'].id if sc['commision_agent_id'] else booking_obj.agent_id.id
                if not agent_commission.get(agent_id, False):
                    agent_commission[agent_id] = 0
                agent_commission[agent_id] += amount

                # ## UPDATED by Samvi 2018/08/14
                # ## Update untuk komisi agent yang tercreate adalah komisi total
                # vals = ledger_env.prepare_vals('Commission : ' + booking_obj.name, booking_obj.name, datetime.now(), 'commission',
                #                                booking_obj.currency_id.id, amount, 0)
                # vals.update({
                #     'transport_booking_id': booking_obj.id,
                #     'agent_id': sc['commision_agent_id'].id and sc['commision_agent_id'].id or booking_obj.agent_id.id,
                #     'pnr': self.pnr,
                #     'description': 'Provider : {}'.format(self.provider),
                # })
                # new_aml = ledger_env.create(vals)
                # new_aml.action_done()

        # ## UPDATED by Samvi 2018/08/14
        # ## Update untuk komisi agent yang tercreate adalah komisi total
        for agent_id, amount in agent_commission.iteritems():
            values = ledger_env.prepare_vals('Commission : ' + booking_obj.name, booking_obj.name, datetime.now(),
                                             'commission', booking_obj.currency_id.id, amount, 0)
            values.update({
                'transport_booking_id': booking_obj.id,
                'agent_id': agent_id,
                'pnr': self.pnr,
                'description': 'Provider : {}'.format(self.provider),
            })
            new_aml = ledger_env.create(values)
            new_aml.action_done()

    def action_issued_provider_api(self, provider_id, api_context):
        try:
            # ## UPDATED by Samvi 2018/07/24
            # ## Terdetect sebagai administrator jika sudo
            # provider_obj = self.env['tt.tb.provider'].sudo().browse(provider_id)
            provider_obj = self.env['tt.tb.provider'].browse(provider_id)
            if not provider_obj:
                return {
                    'error_code': -1,
                    'error_msg': '',
                }
            provider_obj.action_issued(api_context)
            return {
                'error_code': 0,
                'error_msg': '',
            }
        except Exception as e:
            return {
                'error_code': -1,
                'error_msg': str(e)
            }

    def action_fail_issued_provider_api(self, error_msg, provider_id, api_context):
        try:
            # ## UPDATED by Samvi 2018/07/24
            # ## Terdetect sebagai administrator jika sudo
            # provider_obj = self.env['tt.tb.provider'].sudo().browse(provider_id)
            provider_obj = self.env['tt.tb.provider'].browse(provider_id)
            if not provider_obj:
                return {
                    'error_code': -1,
                    'error_msg': '',
                }
            provider_obj.action_fail_issued(error_msg, api_context)
            return {
                'error_code': 0,
                'error_msg': '',
            }
        except Exception as e:
            return {
                'error_code': -1,
                'error_msg': str(e)
            }

    def action_create_ledger(self):
        if not self.is_ledger_created:
            self.write({'is_ledger_created': True})
            self.create_ledger()
            self.create_commission_ledger()
            self.env.cr.commit()

    def action_create_ledger_api(self, provider_id, api_context):
        try:
            # ## UPDATED by Samvi 2018/07/24
            # ## Terdetect sebagai administrator jika sudo
            # provider_obj = self.env['tt.tb.provider'].sudo().browse(provider_id)
            provider_obj = self.env['tt.tb.provider'].browse(provider_id)
            if not provider_obj:
                return {
                    'error_code': -1,
                    'error_msg': 'Provider Data not Found',
                }
            provider_obj.action_create_ledger()
            return {
                'error_code': 0,
                'error_msg': ''
            }
        except Exception as e:
            return {
                'error_code': -1,
                'error_msg': str(e)
            }

    def action_reverse_ledger(self):
        if not self.booking_id.ledger_ids:
            raise UserError('Ledger is null')
        if self.refund_uid or self.refund_date or self.state == 'fail_refunded':
            raise UserError('This PNR has been REFUNDED')
        if not self.is_ledger_created:
            raise UserError('This Provider Ledger is not Created')
        self.write({
            'state': 'fail_refunded',
            'is_ledger_created': False,
            'refund_uid': self.env.user.id,
            'refund_date': datetime.now(),
        })
        self.create_reverse_booking_ledger()
        self.create_reverse_commission_ledger()
        self.booking_id.action_check_provider_state()
        self.env.cr.commit()
        self.booking_id.message_post(body=_("PNR Refunded: {} (Provider : {})".format(self.pnr, self.provider)))

    def create_reverse_booking_ledger(self):
        ledger_env = self.env['tt.ledger'].sudo()
        amount = 0
        for sc in self.cost_service_charge_ids:
            if sc.charge_code.find('r.ac') < 0:
                amount += sc.total
        booking_obj = self.booking_id
        ledger_values = ledger_env.prepare_vals('FRF : ' + booking_obj.name, booking_obj.name,
                                                datetime.now(), 'refund.failed.issue', booking_obj.currency_id.id,
                                                amount, 0)
        ledger_values.update({
            'transport_booking_id': booking_obj.id,
            'agent_id': booking_obj.agent_id.id,
            'pnr': self.pnr,
            'description': 'Refund : {}, PNR : {}, Provider : {}'.format(booking_obj.name, self.pnr, self.provider),
        })
        new_aml = ledger_env.create(ledger_values)
        new_aml.action_done()

    def create_reverse_commission_ledger(self):
        ledger_env = self.env['tt.ledger'].sudo()
        booking_obj = self.booking_id
        agent_commission = {}
        for sc in self.cost_service_charge_ids:
            # Pada lionair ada r.ac positif
            if 'r.ac' in sc.charge_code and sc.total < 0:
                amount = abs(sc.total)
                agent_id = sc['commision_agent_id'].id if sc['commision_agent_id'] else booking_obj.agent_id.id
                if not agent_commission.get(agent_id, False):
                    agent_commission[agent_id] = 0
                agent_commission[agent_id] += amount

                # ## UPDATED by Samvi 2018/08/14
                # ## Update untuk komisi agent yang tercreate adalah komisi total
                # vals = ledger_env.prepare_vals('FRF : ' + booking_obj.name, booking_obj.name, datetime.now(),
                #                                'refund.failed.issue', booking_obj.currency_id.id, 0, amount)
                # vals.update({
                #     'transport_booking_id': booking_obj.id,
                #     'agent_id': sc['commision_agent_id'].id and sc['commision_agent_id'].id or booking_obj.agent_id.id,
                #     'pnr': self.pnr,
                #     'description': 'Refund : {}, PNR : {}, Provider : {}'.format(booking_obj.name, self.pnr, self.provider),
                # })
                # new_aml = ledger_env.create(vals)
                # new_aml.action_done()

        # ## UPDATED by Samvi 2018/08/14
        # ## Update untuk komisi agent yang tercreate adalah komisi total
        for agent_id, amount in agent_commission.iteritems():
            vals = ledger_env.prepare_vals('FRF : ' + booking_obj.name, booking_obj.name, datetime.now(),
                                           'refund.failed.issue', booking_obj.currency_id.id, 0, amount)
            vals.update({
                'transport_booking_id': booking_obj.id,
                'agent_id': agent_id,
                'pnr': self.pnr,
                'description': 'Refund : {}, PNR : {}, Provider : {}'.format(booking_obj.name, self.pnr, self.provider),
            })
            new_aml = ledger_env.create(vals)
            new_aml.action_done()

    def action_get_segments(self):
        res = [{
            'sequence': rec.sequence,
            'segment_code': rec.segment_code,
            'fare_code': rec.fare_code,
            'journey_type': rec.journey_type,
        } for journey in self.journey_ids for rec in journey.segment_ids]
        return res

    def action_sync_repricing(self):
        api_context = {
            'co_uid': self.env.user.id,
        }
        if not self.provider in ['sabre']:
            raise UserError('Provider {} cannot repricing'.format(self.provider))
        req_data = {
            'booking_id': self.booking_id.id,
            'pnr': self.pnr,
            'provider': self.provider,
            'segments': self.action_get_segments(),
            'paxs': self.booking_id.action_get_paxs_info(),
        }
        res = API_CN_AIRLINES.SYNC_REPRICING(req_data, api_context)
        if res['error_code'] != 0:
            raise UserError(res['error_msg'])
        else:
            raise UserError('Repricing Done')

    def action_after_sales_pricing(self):
        transport_env = self.env['tt.transport.booking'].sudo()
        book_info = {'pnr': self.pnr}
        api_context = {
            'uid': self.booking_id.booked_uid.id,
            'co_uid': self.booking_id.booked_uid.id,
            'is_company_website': True,
        }
        res = transport_env.repricing_booking_provider(self.booking_id.id, self.provider, book_info, api_context)
        if res['error_code'] != 0:
            raise UserError('Error : {}'.format(res['error_msg']))

    def get_object_dict(self, obj, key_list):
        res = {}
        for key in key_list:
            res[key] = obj[key] if obj and obj[key] else ''
        return res

    def get_segment_details(self):
        key_list = ['sequence', 'segment_code', 'fare_code', 'subclass', 'class_of_service', 'cabin_class']
        journey_obj = self.journey_ids and self.journey_ids or False
        for journey in journey_obj:
            segment_obj = journey.segment_ids
            res = [self.get_object_dict(rec, key_list) for rec in segment_obj]
        return res

    def get_provider_booking_info_api(self, pnr, provider, kwargs={}):
        try:
            provider_env = self.env['tt.tb.provider'].sudo()
            param = [('pnr', '=', pnr)]
            provider and param.append(('provider', '=', provider))
            providerRS = provider_env.search(param)
            if not providerRS:
                raise RequestException('Provider Object not Found', 500)

            provider_obj = providerRS[-1]
            payload = {
                'id': provider_obj.id,
                'name': provider_obj.booking_id.name,
                'pnr': provider_obj.pnr,
                'contact': provider_obj.booking_id.get_contact_details(),
                'passengers': provider_obj.booking_id.get_passenger_details(),
                'segments': provider_obj.get_segment_details(),
                'state': provider_obj.state,
                'total': provider_obj.total,
            }

            res = {
                'error_code': 0,
                'error_msg': '',
                'response': payload
            }
        except Exception as e:
            res = {
                'error_code': 500,
                'error_msg': str(e),
                'response': ''
            }
        return res
