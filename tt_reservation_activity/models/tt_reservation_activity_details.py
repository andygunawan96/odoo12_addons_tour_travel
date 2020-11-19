from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ReservationActivityDetails(models.Model):
    _name = 'tt.reservation.activity.details'
    _description = 'Rodex Model'

    activity_id = fields.Many2one('tt.master.activity', 'Activity')
    activity_product_id = fields.Many2one('tt.master.activity.lines', 'Activity Product')
    visit_date = fields.Datetime('Visit Date')
    timeslot = fields.Char('Timeslot')
    information = fields.Text('Additional Information')
    provider_booking_id = fields.Many2one('tt.provider.activity', 'Provider Booking', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.activity', related='provider_booking_id.booking_id', string='Order Number', store=True)

    def to_dict(self):
        res = {
            'activity': self.activity_id and self.activity_id.name or '',
            'activity_uuid': self.activity_id and self.activity_id.uuid or '',
            'activity_type': self.activity_product_id and self.activity_product_id.name or '',
            'activity_type_uuid': self.activity_product_id and self.activity_product_id.uuid or '',
            'visit_date': self.visit_date and self.visit_date.strftime('%Y-%m-%d') or '',
            'timeslot': self.timeslot and self.timeslot or '',
            'information': self.information and self.information or ''
        }

        return res
