from odoo import api,fields,models

class TtReservationErrHistory(models.Model):
    _name = 'tt.reservation.err.history'

    res_model = fields.Char('Related Reservation Name', required=True, index=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource')
    error_code = fields.Integer('Error Code')
    error_msg = fields.Char('Error Message')