from odoo import api, fields, models


class VisaOrderHandling(models.Model):
    _name = 'tt.reservation.visa.order.handling'
    _description = 'Reservation Visa Order Handling'

    handling_id = fields.Many2one('tt.master.visa.handling', readonly=1)
    to_passenger_id = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger', readonly=1)
    answer = fields.Boolean('Answer')
    answered = fields.Boolean('Answered', default=False)
