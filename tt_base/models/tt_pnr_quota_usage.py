from odoo import api,fields,models

class TtPnrQuotaUsage(models.Model):
    _name = 'tt.pnr.quota.usage'
    _rec_name = 'pnr_quota_id'
    _description = 'Rodex Model PNR Quota'

    res_model_resv = fields.Char('Res Model')
    res_id_resv = fields.Integer('Res ID')
    res_model_prov = fields.Char('Res Model Provider')
    res_id_prov = fields.Integer('Res ID Provider')
    ref_name = fields.Char('Reference', compute="_compute_ref_name", store=True)
    ref_carriers = fields.Char('Reference', compute="_compute_ref_name", store=True)
    ref_pnrs = fields.Char('Reference', compute="_compute_ref_name", store=True)
    pnr_quota_id = fields.Many2one('tt.pnr.quota', 'Quota')

    @api.depends('res_model_resv','res_id_resv','res_model_prov','res_id_prov')
    def _compute_ref_name(self):
        for rec in self:
            try:
                res_obj = self.env[rec.res_model_resv].browse(rec.res_id_resv)
                prov_obj = self.env[rec.res_model_prov].browse(rec.res_id_prov)
                rec.ref_name = res_obj.name
                carrier_names = set([])
                for journey in prov_obj.journey_ids:
                    for segment in journey.segment_ids:
                        if segment.carrier_id:
                            carrier_names.add(segment.carrier_id.name)
                rec.ref_carriers = ','.join(carrier_names)
                rec.ref_pnrs = prov_obj.pnr
            except:
                rec.ref_name = rec.res_model_resv and rec.res_model_resv.split('.')[-1] or False


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
