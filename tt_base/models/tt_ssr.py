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
    category_id = fields.Many2one('tt.ssr.category', 'Category')
    provider_id = fields.Many2one('tt.provider', required=True)
    line_ids = fields.One2many('tt.ssr.list.line', 'ssr_id', 'Lines')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        line_ids = [rec.to_dict() for rec in self.line_ids]
        res = {
            'name': self.name,
            'code': self.code,
            'description': self.description and self.description or '',
            'category_id': self.category_id and self.category_id.to_dict() or {},
            'provider_id': self.provider_id and self.provider_id.to_dict() or {},
            'line_ids': line_ids
        }
        return res


class TtSSRListLine(models.Model):
    _name = 'tt.ssr.list.line'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    value = fields.Char('Value', default='')
    ssr_id = fields.Many2one('tt.ssr.list', 'SSR', readonly=1)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'value': self.value,
            'ssr_id': self.ssr_id and self.ssr_id.to_dict() or {}
        }
        return res


class TtProviderSSRListInherit(models.Model):
    _inherit = 'tt.provider'

    ssr_ids = fields.One2many('tt.ssr.list', 'provider_id', 'SSRs')

    def to_dict(self):
        ssr_ids = [rec.to_dict() for rec in self.ssr_ids]
        res = super(TtProviderSSRListInherit, self).to_dict()
        res.update({
            'ssr_ids': ssr_ids
        })
        return res
