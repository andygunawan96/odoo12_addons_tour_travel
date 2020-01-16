from odoo import api, fields, models, _


class TtSeatReschedule(models.Model):
    _name = 'tt.seat.reschedule'
    _inherit = 'tt.seat.airline'

    segment_id = fields.Many2one('tt.segment.reschedule', 'Segment')
    dummy_field = fields.Boolean('Generate Passenger List', default=False)

    def get_seat_passenger_domain(self):
        pax_id_list = []
        for rec in self.segment_id.passenger_ids:
            pax_id_list.append(rec.id)
        return [('id', 'in', pax_id_list)]

    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger', domain=get_seat_passenger_domain)

    @api.depends('segment_id', 'dummy_field')
    @api.onchange('segment_id', 'dummy_field')
    def _onchange_domain_passenger(self):
        return {'domain': {
            'passenger_id': self.get_seat_passenger_domain()
        }}

