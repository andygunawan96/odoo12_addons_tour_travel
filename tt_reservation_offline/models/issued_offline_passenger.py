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
    _name = 'issued.offline.passenger'

    iss_off_id = fields.Many2one('issued.offline', 'Issued Offline')
    passenger_id = fields.Many2one('tt.customer', 'Passengers', readonly=True,
                                   states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent')
    pax_type = fields.Selection(PAX_TYPE)  # , related='passenger_id.pax_type'
    ticket_number = fields.Char('Ticket Number.', readonly=True, states={'draft': [('readonly', False)],
                                                                         'confirm': [('readonly', False)],
                                                                         'paid': [('readonly', False)]})
    state = fields.Selection(STATE, string='State', default='draft', related='iss_off_id.state')
