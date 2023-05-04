from odoo import api,fields,models

INVENTORY_TYPE = [
    ('internal', 'Internal'),
    ('external', 'External')
]

class TtPnrQuotaUsage(models.Model):
    _name = 'tt.pnr.quota.usage'
    _rec_name = 'pnr_quota_id'
    _description = 'PNR Quota Usage'
    _order = 'id desc'

    res_model_resv = fields.Char('Res Model')
    res_id_resv = fields.Integer('Res ID')
    res_model_prov = fields.Char('Res Model Provider')
    res_id_prov = fields.Integer('Res ID Provider')
    ref_name = fields.Char('Reference')
    ref_carriers = fields.Char('Carriers')
    ref_pnrs = fields.Char('PNR')
    ref_pax = fields.Integer('Total Passenger')
    ref_r_n = fields.Integer('Room/Night')
    inventory = fields.Selection(INVENTORY_TYPE, 'Inventory')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    amount = fields.Monetary('Amount')
    pnr_quota_state = fields.Selection('Quota State', related='pnr_quota_id.state')
    pnr_quota_id = fields.Many2one('tt.pnr.quota', 'Quota')
    ref_provider_type = fields.Char('Ref Provider Type')
    ref_provider = fields.Char('Ref Provider')
    usage_quota = fields.Integer('Usage Quota')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    active = fields.Boolean('Active', default=True)

    def open_reservation(self):
        try:
            form_id = self.env[self.res_model_resv].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model_resv)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model_resv,
            'res_id': self.res_id_resv,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }
