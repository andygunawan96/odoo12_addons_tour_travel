from odoo import api, fields, models
from odoo.http import request
from ...tools import session
import logging
import json
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class temporaryPayment(models.Model):
    _name = "tt.event.reservation.temporary.payment"
    _description = "Rodex Event Module"

    event_reservation_ids = fields.Many2many('tt.event.reservation', 'rel_event_reservation','event_id', 'temporary_id', 'Event Reservation', readonly=True)
    user_id = fields.Many2one('res.users', 'User ID', readonly=True)
    transfer_image_path = fields.Char('Image Path')
    title = fields.Char('title', readonly=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    def get_data_api(self, user_id):
        data = self.env['tt.event.reservation.temporary.payment'].sudo().search(['user_id', '=', user_id])
        return data

    def set_data_to_paid(self, user_id):
        data = self.env['tt.event.reservation.temporary.payment'].sudo().search(['user_id', '=', user_id])
        for i in data:
            i['event_reservation_id'].action_paid()
            i.unlink()

    def action_paid(self):
        process = []
        unprocess = []
        for rec in self.event_reservation_ids:
            if rec.state in ['confirm']:
                rec.action_paid()
                process.append(rec.pnr)
            else:
                unprocess.append(rec.pnr + '(' + rec.state + ')')
        self.env.cr.commit()
        raise UserError('Processed: ' + str(len(process)) + ' Data(s); UnProcessed:' + ', '.join(unprocess) + '.')