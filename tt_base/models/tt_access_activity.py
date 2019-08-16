from odoo import api, fields, models, _


class TtAccessActivity(models.Model):
    _name = 'tt.access.activity'
    _description = 'Rodex Model'

    type = fields.Selection([('login', 'Login'), ('logout', 'Logout')], 'Activity Type', default='login')
    user_id = fields.Many2one('res.users', 'User')
    user_ip_add = fields.Char('IP Address')
