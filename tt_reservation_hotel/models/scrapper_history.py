from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class ScrapHistory(models.Model):
    _name = 'scrap.history'
    _description = 'Scrap History'

    provider_id = fields.Many2one('res.partner', 'Provider')
    city_id = fields.Many2one('res.city', 'City')
    limit = fields.Integer('Limit per city')
    state = fields.Selection([
        ('ongoing', 'On Going'), ('done', 'Done'),
        ('error', 'Error'),
    ], 'Charge Type')
    line_ids = fields.One2many('scrap.history.line', 'scrap_id', 'Line(s)')

    def request_scrap(self):
        raise UserError(_('Not installed yet.'))


class ScrapHistoryLine(models.Model):
    _name = 'scrap.history.line'
    _order = 'id DESC'
    _description = 'Scrap History Line'

    scrap_id = fields.Many2one('scrap.history', 'Scrap History')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    response = fields.Text('Response Text')
    render_date = fields.Datetime('Render on', help='Render to hotel rec. date')

