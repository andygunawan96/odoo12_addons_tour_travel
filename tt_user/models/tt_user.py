from odoo import models, fields, api, _


class TtUser(models.Model):
    _inherit = 'tt.agent'
    _name = 'tt.user'
    _description = 'Rodex Model'

    def get_user_group_template(self):
        pass
