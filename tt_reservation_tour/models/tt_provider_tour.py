from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
import logging
import traceback

_logger = logging.getLogger(__name__)


class TtProviderTour(models.Model):
    _name = 'tt.provider.tour'
    _rec_name = 'pnr'
    _order = 'departure_date'
    _description = 'Rodex Model'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.tour', 'Order Number', ondelete='cascade')
    balance_due = fields.Float('Balance Due')
    tour_id = fields.Many2one('tt.master.tour', 'Tour')
    departure_date = fields.Datetime('Departure Date')
    return_date = fields.Datetime('Arrival Date')

    sid_issued = fields.Char('SID Issued')#signature generate sendiri

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_tour_booking_id', 'Cost Service Charges')

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
    ticket_ids = fields.One2many('tt.ticket.tour', 'provider_id', 'Ticket Number')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    def action_reverse_ledger_from_button(self):
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

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_booked_api_tour(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
            for rec2 in rec.cost_service_charge_ids:
                rec2.sudo().write({
                    'description': provider_data['pnr']
                })

    def action_issued_api_tour(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
                'balance_due': 0
            })

    def action_failed_booked_api_tour(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked'
            })

    def action_failed_issued_api_tour(self):
        for rec in self:
            rec.write({
                'state': 'fail_issued'
            })

    def action_expired(self):
        self.state = 'cancel2'

    def action_refund(self):
        self.state = 'refund'
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
                'ticket_number': psg.get('ticket_number'),
                'passenger_id': psg_with_no_ticket[idx].id
            }))

        self.write({
            'ticket_ids': ticket_list
        })

    # def update_ticket_api(self,passengers):##isi ticket number
    #     ticket_not_found = []
    #     for psg in passengers:
    #         ticket_found = False
    #         for ticket in self.ticket_ids:
    #             psg_name = ticket.passenger_id.name.replace(' ','').lower()
    #             if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ','').lower() in [psg_name, psg_name*2]:
    #                 ticket.write({
    #                     'ticket_number': psg.get('ticket_number','')
    #                 })
    #                 ticket_found = True
    #                 break
    #         if not ticket_found:
    #             ticket_not_found.append(psg)
    #
    #     for psg in ticket_not_found:
    #         self.write({
    #             'ticket_ids': [(0,0,{
    #                 'ticket_number': psg.get('ticket_number'),
    #                 'pax_type': psg.get('pax_type'),
    #             })]
    #         })

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']
        unused_psg = []

        service_charge_vals_dup1 = []
        service_charge_vals_dup2 = []

        if service_charge_vals[0]['charge_code'] == 'disc':
            for scs in service_charge_vals:
                scs['passenger_tour_ids'] = []
                scs['pax_count'] = 0
                scs['total'] = 0
                for psg in self.ticket_ids:
                    scs['currency_id'] = currency_obj.get_id('IDR')
                    scs['foreign_currency_id'] = currency_obj.get_id('IDR')
                    scs['provider_tour_booking_id'] = self.id
                    scs['passenger_tour_ids'].append(psg.passenger_id.id)
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
                    scs['description'] = self.pnr and self.pnr or ''
                if scs['total'] != 0:
                    scs['passenger_tour_ids'] = [(6, 0, scs['passenger_tour_ids'])]
                    service_chg_obj.create(scs)
            return True

        for scs in service_charge_vals:
            if scs.get('description'):
                scs.pop('description')
            if scs.get('tour_room_id'):
                service_charge_vals_dup1.append(scs)
            else:
                service_charge_vals_dup2.append(scs)

        service_charge_vals_dup = service_charge_vals_dup1 + service_charge_vals_dup2

        for scs in service_charge_vals_dup:
            scs['passenger_tour_ids'] = []
            scs['currency_id'] = currency_obj.get_id('IDR')
            scs['foreign_currency_id'] = currency_obj.get_id('IDR')
            scs['provider_tour_booking_id'] = self.id
            for psg in self.ticket_ids:
                if scs.get('tour_room_id'):
                    if scs['pax_type'] == psg.pax_type and scs['tour_room_id'] == psg.tour_room_id.id:
                        if len(scs['passenger_tour_ids']) < int(scs['pax_count']):
                            scs['passenger_tour_ids'].append(psg.passenger_id.id)
                        else:
                            unused_psg.append(psg)
                else:
                    if scs['pax_type'] == psg.pax_type:
                        if len(scs['passenger_tour_ids']) < int(scs['pax_count']):
                            scs['passenger_tour_ids'].append(psg.passenger_id.id)
                        else:
                            unused_psg.append(psg)
            scs['description'] = self.pnr and self.pnr or ''

        for scs in service_charge_vals_dup:
            while len(scs['passenger_tour_ids']) < int(scs['pax_count']):
                unused_psg_dup = unused_psg
                for idx, psg in enumerate(unused_psg_dup):
                    if scs.get('tour_room_id'):
                        if scs['tour_room_id'] == psg.tour_room_id.id and psg.passenger_id.id not in scs['passenger_tour_ids']:
                            scs['passenger_tour_ids'].append(psg.passenger_id.id)
                            unused_psg.pop(idx)
                            if len(scs['passenger_tour_ids']) >= int(scs['pax_count']):
                                break
                    else:
                        if psg.passenger_id.id not in scs['passenger_tour_ids']:
                            scs['passenger_tour_ids'].append(psg.passenger_id.id)
                            unused_psg.pop(idx)
                            if len(scs['passenger_tour_ids']) >= int(scs['pax_count']):
                                break

        for scs in service_charge_vals_dup:
            if scs.get('tour_room_id'):
                scs.pop('tour_room_id')
            # scs.pop('currency')
            # scs.pop('foreign_currency')
            scs['passenger_tour_ids'] = [(6,0,scs['passenger_tour_ids'])]
            if scs['total'] != 0:
                service_chg_obj.create(scs)

    def delete_service_charge(self):
        for rec in self.cost_service_charge_ids:
            rec.unlink()
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

    def action_create_ledger(self, issued_uid, pay_method=None):
        if pay_method == 'installment':
            total_amount = (self.booking_id.tour_id.down_payment / 100) * self.booking_id.total

            res_model = self.booking_id._name
            res_id = self.booking_id.id
            name = 'Order Down Payment: ' + self.booking_id.name
            ref = self.booking_id.name
            date = datetime.now()+relativedelta(hours=7)
            currency_id = self.booking_id.currency_id.id
            ledger_issued_uid = issued_uid
            agent_id = self.booking_id.agent_id.id
            customer_parent_id = self.booking_id.customer_parent_id.id
            description = 'Ledger for ' + str(self.booking_id.name)
            ledger_type = 2
            debit = 0
            credit = total_amount
            additional_vals = {
                'pnr': self.booking_id.pnr,
                'display_provider_name': self.provider_id.name,
                'provider_type_id': self.provider_id.provider_type_id.id,
            }

            self.env['tt.ledger'].create_ledger_vanilla(res_model, res_id, name, ref, date, ledger_type, currency_id,
                                                        ledger_issued_uid, agent_id, customer_parent_id, debit, credit, description, **additional_vals)
        else:
            self.env['tt.ledger'].action_create_ledger(self, issued_uid)

    def action_create_installment_ledger(self, issued_uid, payment_rules_id, commission_ledger=False):
        try:
            payment_rules_obj = self.env['tt.payment.rules'].sudo().browse(int(payment_rules_id))
            total_amount = (payment_rules_obj.payment_percentage / 100) * self.booking_id.total

            is_enough = self.env['tt.agent'].check_balance_limit_api(self.booking_id.agent_id.id, total_amount)
            if is_enough['error_code'] != 0:
                raise UserError(_('Not Enough Balance.'))

            res_model = self.booking_id._name
            res_id = self.booking_id.id
            name = 'Order ' + payment_rules_obj.name + ': ' + self.booking_id.name
            ref = self.booking_id.name
            date = datetime.now()+relativedelta(hours=7)
            currency_id = self.booking_id.currency_id.id
            ledger_issued_uid = issued_uid
            agent_id = self.booking_id.agent_id.id
            customer_parent_id = False
            description = 'Ledger for ' + str(self.booking_id.name)
            ledger_type = 2
            debit = 0
            credit = total_amount
            additional_vals = {
                'pnr': self.booking_id.pnr,
                'display_provider_name': self.provider_id.name,
                'provider_type_id': self.provider_id.provider_type_id.id,
            }

            self.env['tt.ledger'].create_ledger_vanilla(res_model, res_id, name, ref, date, ledger_type, currency_id,
                                                        ledger_issued_uid, agent_id, customer_parent_id, debit, credit, description, **additional_vals)

            if commission_ledger:
                self.env['tt.ledger'].create_commission_ledger(self, issued_uid)
            return ERR.get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def to_dict(self):
        journey_list = []
        for rec in self.journey_ids:
            journey_list.append(rec.to_dict())
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
            'direction': self.direction,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'return_date': self.return_date,
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
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
