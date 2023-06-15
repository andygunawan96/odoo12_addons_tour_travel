from odoo import api,models,fields
from datetime import datetime
from odoo.exceptions import UserError

class TtReconcileManualMatchWizard(models.TransientModel):
    _name = "tt.reconcile.manual.match.wizard"
    _description = 'Orbis Wizard Reconcile Manual Match Wizard'

    reconcile_transaction_line_id = fields.Many2one('tt.reconcile.transaction.lines','Transaction Line',readonly=True)
    current_total_price = fields.Monetary('Current Total Price',readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)

    provider_selection = fields.Selection(lambda self: self._compute_provider_selection(),'Provider Selection')

    def _compute_provider_selection(self):
        try:
            recon_line_obj = self.env['tt.reconcile.transaction.lines'].browse(int(self._context['default_reconcile_transaction_line_id']))
            search_domain = [
                ('reconcile_line_id', '=', False),
                '|',
                ('pnr', 'ilike', recon_line_obj.pnr),
                ('issued_date', '=', recon_line_obj.reconcile_transaction_id.transaction_date)
            ]
            if self._context.get('offline_provider'):
                provider_type = self.env['tt.provider.offline'].search(search_domain)
            else:
                provider_type = self.env['tt.provider.%s' % (self._context['default_provider_type_code'])].search(search_domain)
            selection = []
            for rec in provider_type:
                selection.append((rec.id,'{}  |  {:,}  |  {}'.format(rec.pnr or '######',rec.vendor_amount and int(rec.vendor_amount) or 0,rec.issued_date and str(rec.issued_date)[:19] or 'No Date')))
            return selection
        except:
            return []

    def select_provider(self):
        if not self.provider_selection:
            raise UserError('Please Select Provider First')
        if self._context.get('offline_provider'):
            found_rec = self.env['tt.provider.offline'].browse(int(self.provider_selection))
        else:
            found_rec = self.env['tt.provider.%s' % (self._context['default_provider_type_code'])].browse(int(self.provider_selection))
        try:
            found_rec.create_date
        except:
            raise UserError('Provider Not Found')
        self.reconcile_transaction_line_id.write({
            'res_model': found_rec._name,
            'res_id': found_rec.id,
            'state': 'match'
        })
        found_rec.write({
            'reconcile_line_id': self.reconcile_transaction_line_id.id,
            'reconcile_time': datetime.now()
        })

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