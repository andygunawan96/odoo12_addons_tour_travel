from odoo import models, fields, api, _


class ApiConnector(models.Model):
    _name = 'tt.api.connector'

    name = fields.Char('Name')
