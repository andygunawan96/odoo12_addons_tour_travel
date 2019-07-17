from odoo import api, fields, models, _
from datetime import datetime


class CancellationPolicy(models.Model):
    _name = 'cancellation.policy'
    _description = 'Cancellation Policy in Object need to convert to string'

    name = fields.Char('Name', required=True)
    max_cancel_days = fields.Integer('Max day(s)', help='Max cancellation date before check in date; set to "-1" if no cancellation allowed for')
    charge_type = fields.Selection([
        ('prc', 'Percentage'),
        ('nom', 'Amount'),
    ], 'Charge Type', Help='perc = 20%; nom = rp. 150k')
    charge_rate = fields.Float('Charge Rate', Help='perc = 20%; nom = rp. 150k')
    charge_rate_currency = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.IDR'))
    description = fields.Text('Descriptions')

    def get_cancellation_policies(self, hotel_id, room_id):
        vals = []
        room_obj = self.env['tt.room.info'].browse(room_id)
        hotel_obj = self.env['tt.hotel'].browse(hotel_id)
        room_policies = room_obj.cancellation_policy
        for policy in room_policies:
            value = {
                'from_date': '',
                'to_date': '',
                'room_name': room_obj.name,
                'max_cancel_days': policy.max_cancel_days,
                'charge_type': policy.charge_type,
                'charge_rate': policy.charge_rate,
                'charge_rate_currency': policy.charge_rate_currency.name or 'IDR',
                'description': policy.description,
            }
            vals.append(value)
        return vals