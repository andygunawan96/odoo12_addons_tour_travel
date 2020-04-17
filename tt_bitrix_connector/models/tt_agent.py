from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)

class TtAgent(models.Model):
    _inherit = 'tt.agent'

    is_using_bitrix = fields.Boolean('Is Using Bitrix', default=False)
    is_default_bitrix_agent = fields.Boolean('Is Default Bitrix Agent', default=False)

    @api.onchange('is_using_bitrix')
    @api.depends('is_using_bitrix')
    def onchange_is_using_bitrix(self):
        if not self.is_using_bitrix:
            self.is_default_bitrix_agent = False

    @api.onchange('is_default_bitrix_agent')
    def onchange_is_default_bitrix_agent(self):
        if self.is_default_bitrix_agent:
            default_agent_list = self.env['tt.agent'].sudo().search([('is_default_bitrix_agent', '=', True), ('id', '!=', self._origin.id)])
            for rec in default_agent_list:
                rec.sudo().write({
                    'is_default_bitrix_agent': False
                })
