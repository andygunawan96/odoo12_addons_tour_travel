from odoo import api,models,fields
from datetime import datetime
from odoo.exceptions import UserError


class TtReconcileTransactionWizard(models.TransientModel):
    _name = "tt.reconcile.transaction.wizard"
    _description = 'Rodex Wizard Reconcile Transaction Wizard'

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_id = fields.Many2one('tt.provider', 'Provider', domain="[('provider_type_id', '=', provider_type_id),('is_reconcile','=',True)]")
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')

    @api.onchange('provider_type_id')
    def _onchange_domain_agent_id(self):
        self.provider_id = False

    @api.onchange('date_from')
    def _onchange_date_from(self):
        self.date_to = self.date_from

    def send_recon_request_data(self):
        request = {
            'provider_type': self.provider_type_id.code,
            'data': {
                'provider': self.provider_id.code,
                'date_from': self.date_from and datetime.strftime(self.date_from,'%Y-%m-%d') or '',
                'date_to': self.date_to and datetime.strftime(self.date_to,'%Y-%m-%d') or ''
            }
        }
        response = self.env['tt.api.con'].send_reconcile_request(request)
        if response['error_code'] != 0:
            raise UserError(response['error_msg'])
        recon_obj_list = self.save_reconcile_data(response['response'])
        return recon_obj_list

    def dummy_send_recon(self):
        request = {
            'provider_type': 'train',
            'data': {
                'provider': 'kai',
                'date_from': '2020-02-10',
                'date_to': '2020-02-11'
            }
        }
        recon_resp = self.env['tt.api.con'].send_reconcile_request(request)
        if recon_resp['error_code'] != 0:
            raise UserError("Failed")
        self.save_reconcile_data(recon_resp['response'])

    def save_reconcile_data(self,data):
        provider_obj = self.env['tt.provider'].search([('code','=',data['provider_code'])])
        if not provider_obj:
            raise UserError("Provider Not Found")
        recon_data_list = []
        for period in data['transaction_periods']:
            existing_recon_data = self.env['tt.reconcile.transaction'].search([('provider_id','=',provider_obj.id),
                                                                               ('transaction_date','=',period['transaction_date'])])
            if existing_recon_data:
                recon_data = existing_recon_data
            else:
                recon_data = self.env['tt.reconcile.transaction'].create({
                    'provider_id': provider_obj.id,
                    'transaction_date': period['transaction_date']
                })

            write_data = []
            for transaction in period['transactions']:
                try:
                    currency = self.env.ref("base." + transaction['currency']).id
                    transaction.update({
                        'currency_id': currency,
                    })
                except:
                    pass

                try:
                    vendor_balance_currency = self.env.ref("base." + transaction['vendor_balance_currency']).id
                    transaction.update({
                        'vendor_balance_currency_id': vendor_balance_currency,
                    })
                except:
                    pass

                trans_lines = recon_data.reconcile_lines_ids.filtered(lambda x: x.pnr == transaction['pnr'] and x.type == transaction['type'])
                if trans_lines:
                    if transaction['sequence'] != trans_lines[0].sequence:  # update sequence dari vendor
                        trans_lines[0].sequence = transaction['sequence']
                    if trans_lines[0].total == transaction['total'] or trans_lines[0].state == 'match':
                        continue
                    else:
                        write_data.append((1,trans_lines[0].id,transaction))
                else:
                    if transaction['type'] == 'nta':
                        transaction['state'] = 'not_match'
                    else:
                        transaction['state'] = 'done'
                    write_data.append((0,0,transaction))

            recon_data.write({
                'reconcile_lines_ids': write_data
            })
            recon_data.action_sync_balance()
            recon_data_list.append(recon_data)
        return recon_data_list

    # TODO: pindah kan ke lokasi yg tepat
    def reconcile_internal_vendor(self, req):
        '''
        :param req:{
            'type': 'airline', #Opsi = ['airline', 'hotel', 'train', 'event']
            'from_date': '2020-07-21', #YYYY-MM-DD
            'to_date': '2020-07-22', #YYYY-MM-DD
        }
        :return:
        '''
        self.env['tt.reservation.' + req['type']].search([
            ('issued_date', '<=', req['from_date']), ('issued_date', '>=', req['to_date']),
            ('reconcile_state', '=', 'reconciled')
        ])
        return True
