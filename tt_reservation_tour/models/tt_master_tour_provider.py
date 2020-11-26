from odoo import api, fields, models, _


class MasterTourProvider(models.Model):
    _name = 'tt.master.tour.provider'
    _rec_name = 'provider_id'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='provider_id.provider_type_id',
                                       store=True, readonly=True)
    master_tour_id = fields.Many2one('tt.master.tour', 'Master Tour', required=True, readonly=True)
    description = fields.Text('Provider Coverage Details')
    letter_of_guarantee_ids = fields.One2many('tt.letter.guarantee', 'res_id', 'Letter of Guarantee(s)')

