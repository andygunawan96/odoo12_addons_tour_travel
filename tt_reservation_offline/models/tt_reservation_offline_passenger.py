from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables

PAX_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('refund', 'Refund'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
]


class IssuedOfflinePassenger(models.Model):
    _name = 'tt.reservation.offline.passenger'
    _inherit = 'tt.reservation.passenger'
    _description = 'Rodex Model'

    booking_id = fields.Many2one('tt.reservation.offline', 'Issued Offline')
    passenger_id = fields.Many2one('tt.customer', 'Passengers', readonly=True,
                                   states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True, default=lambda self: self.env.user.agent_id.id)
    pax_type = fields.Selection(PAX_TYPE)  # , related='passenger_id.pax_type'
    transaction_name = fields.Char('Transaction Name', related='booking_id.provider_type_id_name')
    ticket_number = fields.Char('Ticket Number.', readonly=True, states={'draft': [('readonly', False)],
                                                                         'confirm': [('readonly', False)]})
    seat = fields.Char('Seat', readonly=True, states={'draft': [('readonly', False)],
                                                      'confirm': [('readonly', False)]})
    state = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state')
    state_offline = fields.Selection(STATE, string='State', default='draft', related='booking_id.state_offline')
    first_name = fields.Char('First Name', related='passenger_id.first_name')
    last_name = fields.Char('Last Name', related='passenger_id.last_name')
    title = fields.Selection(variables.TITLE, 'Title')
    birth_date = fields.Date('Birth Date')

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_offline_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_offline_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')

    def to_dict(self):
        res = {
            'ticket_number': self.ticket_number if self.ticket_number else '',
            'pax_type': self.pax_type if self.pax_type else '',
            'first_name': self.first_name if self.first_name else '',
            'last_name': self.last_name if self.last_name else '',
            'title': self.title if self.title else '',
            'birth_date': str(self.birth_date) if self.birth_date else ''
        }
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    # def compute_agent_id(self):
    #     self.agent_id = self.booking_id.sub_agent_id
