from odoo import api, fields, models, _
import traceback,logging
from odoo.exceptions import UserError
from ...tools import ERR, variables

_logger = logging.getLogger(__name__)


class TtReservationPassengerAirlineEditWizard(models.TransientModel):
    _name = "tt.reservation.passenger.airline.edit.wizard"
    _description = 'Reservation Passenger Airline Edit Wizard'

    reservation_passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Reservation Passenger', readonly=True)
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    title = fields.Selection(variables.TITLE, string='Title')

    def submit_edit_reservation_passenger(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 109')
        temp_name = ''
        if self.first_name:
            temp_name += self.first_name
        if self.last_name:
            temp_name += " %s" % self.last_name
        self.reservation_passenger_id.write({
            'first_name': self.first_name and self.first_name or '',
            'last_name': self.last_name and self.last_name or '',
            'name': temp_name,
            'title': self.title,
        })
        if self.env.user.has_group('tt_base.group_customer_level_3'):
            temp_marital = self.reservation_passenger_id.customer_id.marital_status and self.reservation_passenger_id.customer_id.marital_status or 'single'
            if self.title in ['MRS', 'MS', 'MISS']:
                temp_gender = 'female'
                if self.title == 'MRS':
                    temp_marital = 'married'
            else:
                temp_gender = 'male'
            write_vals = {
                'first_name': self.first_name,
                'last_name': self.last_name,
                'gender': temp_gender,
                'marital_status': temp_marital
            }
            self.reservation_passenger_id.customer_id.write(write_vals)
            self.reservation_passenger_id.customer_id._compute_name()
