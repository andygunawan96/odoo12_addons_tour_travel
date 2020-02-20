from odoo import api,fields,models

class TtPnrQuota(models.Model):
    _name = 'tt.pnr.quota'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota'

    name = fields.Char('Name', related='price_list_id.name')
    amount = fields.Integer('Amount')
    price_list_id = fields.Many2one('tt.pnr.quota.price.list', 'Price Data')
    expired_date = fields.Date('Expired Date')
    usage_ids = fields.One2many('tt.pnr.quota.usage','pnr_quota_id','Quota Usage')
    agent_id = fields.Many2one('tt.agent','Agent')