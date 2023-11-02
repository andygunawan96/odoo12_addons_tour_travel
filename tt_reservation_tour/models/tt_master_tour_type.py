from odoo import api, fields, models, _


class TtMasterTourType(models.Model):
    _name = 'tt.master.tour.type'
    _description = 'Master Tour Type'

    name = fields.Char('Name', required=True)
    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    description = fields.Text('Description')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True,
                            default=lambda self: self.env.user.ho_id.id)
    is_can_choose_hotel = fields.Boolean('Can Choose Hotel')
    is_use_tour_leader = fields.Boolean('Is Use Tour Leader')
    is_open_date = fields.Boolean('Is Open Date')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('master.tour.type')
        return super(TtMasterTourType, self).create(vals_list)

    def to_dict(self):
        return {
            'name': self.name,
            'seq_id': self.seq_id,
            'description': self.description and self.description or '',
            'is_can_choose_hotel': self.is_can_choose_hotel,
            'is_use_tour_leader': self.is_use_tour_leader,
            'is_open_date': self.is_open_date
        }
