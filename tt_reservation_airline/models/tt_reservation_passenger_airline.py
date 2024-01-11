from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.airline'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Airline'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    fee_ids = fields.One2many('tt.fee.airline', 'passenger_id', 'SSR')
    booking_id = fields.Many2one('tt.reservation.airline')
    is_ticketed = fields.Boolean('Ticketed')
    riz_text = fields.Char('Endorsement Box (RIZ)', default='')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        fee_list = []
        for rec in self.fee_ids:
            fee_list.append(rec.to_dict())
        sale_service_charges = self.get_service_charges()

        if self.booking_id and self.booking_id.ho_id:
            pricing_breakdown = self.booking_id.ho_id.get_ho_pricing_breakdown()
            if pricing_breakdown:
                service_charge_details = self.get_service_charge_details_breakdown()
            else:
                service_charge_details = self.get_service_charge_details_no_breakdown()
        else:
            service_charge_details = self.get_service_charge_details()

        pax_type = ''
        for pnr in sale_service_charges:
            for svc in sale_service_charges[pnr]:
                pax_type = sale_service_charges[pnr][svc]['pax_type']
                break
            break
        res.update({
            'sale_service_charges': sale_service_charges,
            'service_charge_details': service_charge_details,
            'fees': fee_list,
            'behaviors': self.customer_id.get_behavior(),
            'seq_id': self.customer_id.seq_id,
            'pax_type': pax_type,
            'riz_text': self.riz_text if self.riz_text else ''
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    def create_ssr(self,ssr_param,pnr,provider_id, is_create_service_charge=True):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']
        ssr_list = []
        for ssr in ssr_param:
            amount = 0
            currency_id = False
            # September 10, 2021 - SAM
            # Fix amount 0 apabila booking telah terissued.
            for sc in ssr['service_charges']:
                # FIXME sementara default IDR
                currency = sc['currency'] if sc.get('currency') else 'IDR'
                foreign_currency = sc['foreign_currency'] if sc.get('foreign_currency') else 'IDR'
                currency_id = currency_obj.search([('name', '=', currency)], limit=1).id
                ho_obj = False
                if self.booking_id and self.booking_id.agent_id:
                    ho_obj = self.booking_id.agent_id.ho_id
                if ho_obj:
                    sc['ho_id'] = ho_obj.id
                sc['currency_id'] = currency_id
                sc['foreign_currency_id'] = currency_obj.search([('name','=', foreign_currency)],limit=1).id
                sc['description'] = pnr
                sc['passenger_airline_ids'] = [(4,self.id)]
                sc['provider_airline_booking_id'] = provider_id
                sc['is_extra_fees'] = True
                amount += sc['amount']
                if is_create_service_charge:
                    service_chg_obj.create(sc)

            ssr_values = {
                'name': ssr['fee_name'],
                'type': ssr['fee_type'],
                'code': ssr['fee_code'],
                'value': ssr['fee_value'],
                'category': ssr.get('fee_category', False),
                'description': json.dumps(ssr['description']),
                'amount': amount,
                'passenger_id': self.id,
                'pnr': pnr,
                'provider_id': provider_id,
                'journey_code': ssr['journey_code'],
                'ticket_number': ssr.get('ticket_number', ''),
            }
            if currency_id:
                ssr_values['currency_id'] = currency_id
            ssr_list.append((0,0,ssr_values))

        self.write({'fee_ids': ssr_list})





