from odoo import api,models,fields
from datetime import datetime
from odoo.exceptions import UserError

class TtReconcileManualMatchWizard(models.TransientModel):
    _name = "tt.reconcile.manual.match.wizard"
    _description = 'Rodex Wizard Reconcile Manual Match Wizard'

    current_record_pnr = fields.Char('Current PNR', readonly=True)
    current_total_price = fields.Monetary('Current Total Price',readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)

    provider_selection = fields.Selection(lambda self: self._compute_provider_selection(),'Provider Selection')

    def _compute_provider_selection(self):
        try:
            provider_type = self.env['tt.provider.%s' % (self._context['default_provider_type_code'])].search([
                ('reconcile_line_id','=',False)
            ])
            selection = []
            for rec in provider_type:
                selection.append((rec.id,'%s - %s' % (rec.pnr or '######',rec.total_price)))
            return selection
        except:
            return []

    # def match_data(self):
    #     if not self.provider_selection:
    #         raise UserError('Please Select Provider First')
    #
    #     self.write({
    #         'res_model': found_rec._name,
    #         'res_id': found_rec.id,
    #         'state': 'match'
    #     })
    #     found_rec.write({
    #         'reconcile_line_id': rec.id,
    #         'reconcile_time': datetime.now()
    #     })

    def open_reference(self):
        if not self.provider_selection:
            raise UserError('Please Select Provider First')

        res_model = 'tt.provider.%s' % (self._context['default_provider_type_code'])
        form_id = self.env['ir.ui.view'].search([('type', '=', 'form'),
                                                 ('model', '=', res_model)], limit=1)
        form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Provider',
            'res_model': res_model,
            'res_id': int(self.provider_selection),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'new',
        }