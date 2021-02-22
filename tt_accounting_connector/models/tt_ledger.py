from odoo import api, fields, models, modules, tools
from ..accounting_models.tt_accounting_connector import SalesOrder
import logging, traceback
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    @api.model
    def create(self, vals):
        ledger = super(TtLedger, self).create(vals)
        # self.env.cr.commit()

        try:
            ho_name_search = self.env.ref('tt_base.rodex_ho')
            ho_name = ho_name_search.name
            pay_method = ''
            pay_acquirer = ''
            nta = 0
            is_last_ledger = False
            target_obj = self.env[ledger.res_model].sudo().browse(ledger.res_id)
            ledger_objs = []
            if 'ledger_ids' in target_obj._fields:
                tot_debit = 0
                tot_credit = 0
                for rec in target_obj.ledger_ids:
                    tot_debit += rec.debit
                    tot_credit += rec.credit
                    temp_dict = {
                        'obj': rec,
                        'reference_num': target_obj.name,
                        'sender': target_obj.agent_id and target_obj.agent_id.name,
                        'trans_type': ACC_TRANSPORT_TYPE[rec.res_model],
                    }
                    if ledger.res_model == 'tt.refund':
                        pass
                    elif ledger.res_model == 'tt.reschedule':
                        pass
                    elif ledger.res_model == 'tt.adjustment':
                        temp_dict.update({
                            'nta': target_obj.adjust_amount
                        })
                        if tot_credit == target_obj.adjust_amount or tot_debit == target_obj.adjust_amount:
                            is_last_ledger = True
                    elif ledger.res_model == 'tt.agent.invoice':
                        temp_dict.update({
                            'nta': rec.debit > 0 and rec.debit or rec.credit
                        })
                        is_last_ledger = True
                    elif ledger.res_model == 'tt.top.up':
                        pass
                    else:
                        temp_dict.update({
                            'nta': target_obj.total_nta
                        })
                        if tot_credit == target_obj.total and tot_debit == target_obj.total_commission:
                            is_last_ledger = True
                    ledger_objs.append(temp_dict)

            if is_last_ledger:
                url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                submitted_data = []
                for current_ledger in ledger_objs:
                    temp_debit = current_ledger['obj'].debit and current_ledger['obj'].debit or 0
                    temp_credit = current_ledger['obj'].credit and current_ledger['obj'].credit or 0
                    temp_transac_type = dict(self._fields['transaction_type'].selection).get(current_ledger['obj'].transaction_type)
                    if current_ledger['obj'].transaction_type == 3:
                        if current_ledger['obj'].agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
                            temp_transac_type += ' HO'
                        else:
                            temp_transac_type += ' Channel'
                    if temp_debit < 0:
                        temp_credit = temp_debit * -1
                        temp_debit = 0
                    if temp_credit < 0:
                        temp_debit = temp_credit * -1
                        temp_credit = 0
                    if temp_transac_type == 'Refund' and temp_credit > 0:
                        temp_transac_type = 'Admin Fee'
                    submitted_data.append({
                        'reference_number': current_ledger['reference_num'],
                        'name': current_ledger['obj'].name,
                        'debit': temp_debit,
                        'credit': temp_credit,
                        'currency_id': 'IDR',
                        'create_date': current_ledger['obj'].create_date,
                        'date': current_ledger['obj'].date,
                        'create_uid': current_ledger['obj'].create_uid.name,
                        'commission': 0.0,
                        'description': current_ledger['obj'].description and current_ledger['obj'].description or '',
                        'agent_id': current_ledger['obj'].agent_id and current_ledger['obj'].agent_id.name or (current_ledger['obj'].customer_parent_id and current_ledger['obj'].customer_parent_id.name or ''),
                        'company_sender': current_ledger['sender'],
                        'company_receiver': ho_name,
                        'state': 'Done',
                        'display_provider_name': current_ledger['obj'].display_provider_name and current_ledger['obj'].display_provider_name or '',
                        'pnr': current_ledger['obj'].pnr and current_ledger['obj'].pnr or '',
                        'url_legacy': url + '/web#id=' + str(current_ledger['obj'].id) + '&model=tt.ledger&view_type=form',
                        'transaction_type': temp_transac_type,
                        'transport_type': current_ledger['trans_type'],
                        'payment_method': pay_method and pay_method or '',
                        'NTA_amount_real': current_ledger['nta'],
                        'payment_acquirer': pay_acquirer and pay_acquirer or '',
                    })

                so = SalesOrder()
                temp = json.dumps(submitted_data)
                res = so.AddSalesOrder(temp)
                t_type = submitted_data[0]['transport_type']
                if res.get('status_code') == 200:
                    self.env['tt.accounting.history'].sudo().create({
                        'request': temp,
                        'response': res,
                        'transport_type': t_type,
                        'res_model': ACC_TRANSPORT_TYPE_REVERSE[t_type],
                        'state': 'success'
                    })
                else:
                    self.env['tt.accounting.history'].sudo().create({
                        'request': temp,
                        'response': 'Failed: ' + str(res),
                        'transport_type': t_type,
                        'res_model': ACC_TRANSPORT_TYPE_REVERSE[t_type],
                        'state': 'failed'
                    })
        except Exception as e:
            _logger.error('Error: Failed to create Accounting Data. \n %s : %s' % (traceback.format_exc(), str(e)))
            self.env['tt.accounting.history'].sudo().create({
                'request':'none',
                'response': str(e),
                'state': 'odoo_failed'
            })
        return ledger
