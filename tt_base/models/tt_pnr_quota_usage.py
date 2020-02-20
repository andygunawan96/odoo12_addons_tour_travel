from odoo import api,fields,models

class TtPnrQuotaUsage(models.Model):
    _name = 'tt.pnr.quota.usage'
    _rec_name = 'pnr_quota_id'
    _description = 'Rodex Model PNR Quota'

    res_model = fields.Char('Res Model')
    res_id = fields.Char('Res ID')
    pnr_quota_id = fields.Many2one('tt.pnr.quota', 'Quota')