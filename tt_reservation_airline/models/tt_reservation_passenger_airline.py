from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.airline'
    _inherit = 'tt.reservation.passenger'
    _description = 'Rodex Model'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    fee_ids = fields.One2many('tt.fee.airline', 'passenger_id', 'SSR')
    booking_id = fields.Many2one('tt.reservation.airline')
    is_ticketed = fields.Boolean('Ticketed')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        fee_list = []
        for rec in self.fee_ids:
            fee_list.append(rec.to_dict())
        res.update({
            'sale_service_charges': self.get_service_charges(),
            'fees': fee_list
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    def create_ssr(self,ssr_param,pnr,provider_id):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']
        ssr_list = []
        for ssr in ssr_param:
            amount = 0
            currency_id = False
            for sc in ssr['service_charges']:
                currency_id = currency_obj.search([('name', '=', sc.pop('currency'))], limit=1).id
                sc['currency_id'] = currency_id
                sc['foreign_currency_id'] = currency_obj.search([('name','=',sc.pop('foreign_currency'))],limit=1).id
                sc['description'] = pnr
                sc['passenger_airline_ids'] = [(4,self.id)]
                sc['provider_airline_booking_id'] = provider_id
                sc['is_extra_fees'] = True
                amount += sc['amount']
                service_chg_obj.create(sc)
            ssr_values = {
                'name': ssr['fee_name'],
                'type': ssr['fee_type'],
                'code': ssr['fee_code'],
                'value': ssr['fee_value'],
                'description': json.dumps(ssr['description']),
                'amount': amount,
                'passenger_id': self.id,
            }
            if currency_id:
                ssr_values['currency_id'] = currency_id
            ssr_list.append((0,0,ssr_values))

        self.write({'fee_ids': ssr_list})





