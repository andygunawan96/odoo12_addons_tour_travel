import datetime

from odoo import models, fields, api, _
from ...tools import variables

class ApiBlackout(models.Model):
    _name = 'tt.api.blackout'
    _description = 'API Blackout'

    name = fields.Char("Name")
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date", required=True)
    active = fields.Boolean("Active",default=True)
    config_id = fields.Many2one(comodel_name='tt.api.config', string='Config ID')

    def to_dict(self):
        return {
            "start_date": datetime.datetime.strftime(self.start_date,"%Y-%m-%d"),
            "end_date": datetime.datetime.strftime(self.end_date,"%Y-%m-%d")
        }


    def get_credential(self):
        return {
            "start_date": datetime.datetime.strftime(self.start_date, "%Y-%m-%d"),
            "end_date": datetime.datetime.strftime(self.end_date, "%Y-%m-%d")
        }

class ApiConfigBlackoutInherit(models.Model):
    _inherit = 'tt.api.config'

    blackout_ids = fields.One2many(comodel_name='tt.api.blackout',inverse_name='config_id',string='Blackout Date')

    def to_dict(self):
        res = super(ApiConfigBlackoutInherit, self).to_dict()
        blackout_ids = [rec.to_dict() for rec in self.blackout_ids if rec.active]
        res.update({
            'blackouts_ids': blackout_ids
        })
        return res

    def get_credential(self):
        res = super(ApiConfigBlackoutInherit, self).get_credential()
        blackouts = [rec.get_credential() for rec in self.blackout_ids if rec.active]
        res.update({
            'blackouts': blackouts
        })
        return res