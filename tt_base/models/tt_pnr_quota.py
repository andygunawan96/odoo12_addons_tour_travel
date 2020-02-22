from odoo import api,fields,models

class TtPnrQuota(models.Model):
    _name = 'tt.pnr.quota'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota'

    name = fields.Char('Name', related='price_list_id.name')
    used_amount = fields.Integer('Used Amount', compute='_compute_used_amount',store=True)
    available_amount = fields.Integer('Used Amount', compute='_compute_used_amount',store=True)
    amount = fields.Integer('Amount', compute='_compute_amount', store=True)
    price_list_id = fields.Many2one('tt.pnr.quota.price.list', 'Price Data')
    expired_date = fields.Date('Expired Date')
    usage_ids = fields.One2many('tt.pnr.quota.usage','pnr_quota_id','Quota Usage')
    agent_id = fields.Many2one('tt.agent','Agent')
    is_expired = fields.Boolean('Expired')

    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.price_list_id and rec.price_list_id.amount or False

    @api.depends('usage_ids')
    def _compute_used_amount(self):
        for rec in self:
            rec.used_amount = len(rec.usage_ids.ids)
            rec.available_amount = rec.amount -rec.used_amount
