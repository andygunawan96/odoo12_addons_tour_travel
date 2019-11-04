from odoo import api, fields, models


class MasterVisaHandling(models.Model):
    _name = 'tt.master.visa.handling'
    _rec_name = 'name'
    _description = 'New Description'

    name = fields.Char('Question')
    sequence = fields.Integer('Sequence')
