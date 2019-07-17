from odoo import models, fields, api, _

PAX_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Request'),
    ('valid', 'Validated'),
    ('final', 'Finalization'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
]


class IssuedOfflinePassenger(models.Model):
    _name = 'tt.reservation.offline.passenger'

    booking_id = fields.Many2one('tt.reservation.offline', 'Issued Offline')
    passenger_id = fields.Many2one('tt.customer', 'Passengers', readonly=True,
                                   states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True, default=lambda self: self.env.user.agent_id.id)
    pax_type = fields.Selection(PAX_TYPE)  # , related='passenger_id.pax_type'
    ticket_number = fields.Char('Ticket Number.', readonly=True, states={'draft': [('readonly', False)],
                                                                         'confirm': [('readonly', False)],
                                                                         'paid': [('readonly', False)]})
    state = fields.Selection(STATE, string='State', default='draft', related='booking_id.state')

    # def compute_agent_id(self):
    #     self.agent_id = self.booking_id.sub_agent_id
