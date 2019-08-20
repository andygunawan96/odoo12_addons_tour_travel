from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class ActivityCategory(models.Model):
    _name = 'tt.activity.category'

    name = fields.Char('Name')
    # uuid = fields.Char('Uuid')
    type = fields.Selection([('category', 'Category'), ('type', 'Type')], default='category')
    parent_id = fields.Many2one('tt.activity.category', string='Parent')
    child_ids = fields.One2many('tt.activity.category', 'parent_id')
    # provider_id = fields.Many2one('tt.provider', 'Vendor')
    line_ids = fields.One2many('tt.activity.category.lines', 'category_id')


class ActivityCategoryLines(models.Model):
    _name = 'tt.activity.category.lines'

    category_id = fields.Many2one('tt.activity.category', 'Category ID')
    uuid = fields.Char('Uuid')
    provider_id = fields.Many2one('tt.provider', 'Provider')


