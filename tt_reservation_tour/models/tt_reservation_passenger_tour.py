from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.tour'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Tour'

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_tour_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_tour_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.tour', 'Tour Booking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type')
    tour_room_id = fields.Many2one('tt.master.tour.rooms', 'Room')
    tour_room_seq = fields.Char('Room Sequence')
    master_tour_id = fields.Many2one('tt.master.tour', 'Tour')
    master_tour_line_id = fields.Many2one('tt.master.tour.lines', 'Tour Line')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        sale_service_charges = self.get_service_charges()
        pax_type = ''
        for pnr in sale_service_charges:
            for svc in sale_service_charges[pnr]:
                pax_type = sale_service_charges[pnr][svc]['pax_type']
                break
            break
        res.update({
            'tour_room_id': self.tour_room_id and self.tour_room_id.id or 0,
            'pax_type': self.pax_type and self.pax_type or '',
            'sale_service_charges': sale_service_charges,
            'service_charge_details': self.get_service_charge_details()
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res



