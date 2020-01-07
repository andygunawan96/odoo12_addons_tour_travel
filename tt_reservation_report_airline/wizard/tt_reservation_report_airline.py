from odoo import fields, models, api

STATE = [
    ('all', 'All'),
    ('booked', 'Booked'),
    ('issued', 'Issued'),
    ('expired', 'Expired'),
    ('issue-expired', 'Issue and Expired'),
    ('others', 'Others')
]

class ReservationReportAirline(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = "tt.reservation.report.airline.wizard"

    state = fields.Selection(selection=STATE, string="State", default='all')
