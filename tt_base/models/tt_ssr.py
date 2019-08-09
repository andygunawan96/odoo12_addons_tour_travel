from odoo import api, fields, models, _


class TtSSRCategory(models.Model):
    _name = 'tt.ssr.category'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'active': self.active,
        }
        return res


class TtSSRList(models.Model):
    _name = 'tt.ssr.list'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', default='')
