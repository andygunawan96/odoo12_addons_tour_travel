from odoo import models, fields, api, _
from ...tools.api import Response


class ErrorApi(models.Model):
    _name = 'tt.error.api'
    _description = 'Error API'
    _order = 'code'

    code = fields.Integer(string='Code', help='Error code', required=True)
    message = fields.Char(string='Message', help='Error message', required=True)
    note = fields.Char(string='Note', help='Error note', default="")
    description = fields.Text(string='Description', default="")
    active = fields.Boolean(string='Active', default=True)
    is_data = fields.Boolean(string='System Data', readonly=1, help='to detect if record from data or not', default=0)

    def to_dict(self):
        res = {
            'code': self.code,
            'message': self.message,
            'note': self.note,
            'description': self.description,
        }
        return res

    def get_dict_by_int_code(self):
        _objects = self.sudo().search([('active', '=', 1)])
        res = {}
        [res.update({int(rec.code): rec.to_dict()}) for rec in _objects]
        return res

    def get_dict_by_code(self):
        _objects = self.sudo().search([('active', '=', 1)])
        res = {}
        # April 8, 2019 - SAM
        # Saat parsing value dengan key integer, ada library yang tidak support key dict nya integer
        # Jadi diubah ke string untuk key dictnya
        [res.update({str(rec.code): rec.to_dict()}) for rec in _objects]
        return res

    def get_error_code_api(self):
        try:
            response = self.get_dict_by_code()
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res
