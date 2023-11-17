from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.train'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Train'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_train_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_train_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.train')
    is_ticketed = fields.Boolean('Ticketed')

    temporary_field = fields.Char('Temporary field')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        sale_service_charges = self.get_service_charges()
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
            'temporary_field': json.loads(self.temporary_field) if self.temporary_field else [],
            'behaviors': self.customer_id.get_behavior(),
            'seq_id': self.customer_id.seq_id,
            'pax_type': pax_type
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




