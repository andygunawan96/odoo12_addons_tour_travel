from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
from datetime import datetime, date, timedelta
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtReschedule(models.Model):
    _inherit = 'tt.reschedule'

    posted_acc_actions = fields.Char('Posted to Accounting after Recon', default='')

    def send_ledgers_to_accounting(self, func_action, vendor_list):
        try:
            res = []
            ho_obj = self.agent_id.ho_id
            for ven in vendor_list:
                search_params = [('res_model', '=', self._name), ('res_id', '=', self.id),
                                 ('action', '=', func_action), ('accounting_provider', '=', ven)]
                if ho_obj:
                    search_params.append(('ho_id', '=', ho_obj.id))
                data_exist = self.env['tt.accounting.queue'].search(search_params)
                if data_exist:
                    new_obj = data_exist[0]
                else:
                    new_obj = self.env['tt.accounting.queue'].create({
                        'accounting_provider': ven,
                        'transport_type': ACC_TRANSPORT_TYPE.get(self._name, ''),
                        'action': func_action,
                        'res_model': self._name,
                        'res_id': self.id,
                        'ho_id': ho_obj and ho_obj.id or False
                    })
                res.append(new_obj.to_dict())
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.info("Failed to send ledgers to accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)

    def validate_reschedule_from_button(self, agent_payment_method='balance'):
        super(TtReschedule, self).validate_reschedule_from_button(agent_payment_method)
        if self.agent_id.is_sync_to_acc:
            temp_post = self.posted_acc_actions or ''
            ho_obj = self.agent_id and self.agent_id.ho_id or False
            search_params = [('cycle', '=', 'real_time'), ('is_send_reschedule', '=', True)]
            if ho_obj:
                search_params.append(('ho_id', '=', ho_obj.id))
            setup_list = self.env['tt.accounting.setup'].search(search_params)
            if setup_list:
                vendor_list = []
                for rec in setup_list:
                    if rec.accounting_provider not in vendor_list:
                        vendor_list.append(rec.accounting_provider)
                self.send_ledgers_to_accounting('validate', vendor_list)
                if temp_post:
                    temp_post += ',validate'
                else:
                    temp_post += 'validate'
                self.write({
                    'posted_acc_actions': temp_post
                })

    def cancel_reschedule_from_button(self):
        super(TtReschedule, self).cancel_reschedule_from_button()
        if self.agent_id.is_sync_to_acc:
            temp_post = self.posted_acc_actions or ''
            ho_obj = self.agent_id and self.agent_id.ho_id or False
            search_params = [('cycle', '=', 'real_time'), ('is_send_reschedule', '=', True), ('is_send_reverse_transaction', '=', True)]
            if ho_obj:
                search_params.append(('ho_id', '=', ho_obj.id))
            setup_list = self.env['tt.accounting.setup'].search(search_params)
            if setup_list:
                vendor_list = []
                for rec in setup_list:
                    if rec.accounting_provider not in vendor_list:
                        vendor_list.append(rec.accounting_provider)
                self.send_ledgers_to_accounting('cancel', vendor_list)
                if temp_post:
                    temp_post += ',cancel'
                else:
                    temp_post += 'cancel'
                self.write({
                    'posted_acc_actions': temp_post
                })

    def send_transaction_batches_to_accounting(self, days, ho_id):
        start_datetime = datetime.strptime((date.today() - timedelta(days=days)).strftime('%Y-%m-%d') + ' 00:00:00', "%Y-%m-%d %H:%M:%S")
        transaction_list = self.env['tt.reschedule'].search([('state', 'in', ['final', 'done']), ('final_date', '>=', start_datetime), ('ho_id','=', ho_id)])
        for rec in transaction_list:
            if rec.agent_id.is_sync_to_acc:
                temp_post = rec.posted_acc_actions or ''
                if 'reconcile' not in temp_post.split(',') and 'transaction_batch' not in temp_post.split(','):
                    ho_obj = rec.agent_id and rec.agent_id.ho_id or False
                    search_params = [('cycle', '=', 'per_batch'), ('is_recon_only', '=', False), ('is_send_reschedule', '=', True)]
                    if ho_obj:
                        search_params.append(('ho_id', '=', ho_obj.id))
                    setup_list = self.env['tt.accounting.setup'].search(search_params)
                    if setup_list:
                        vendor_list = []
                        for rec2 in setup_list:
                            if rec2.accounting_provider not in vendor_list:
                                vendor_list.append(rec2.accounting_provider)
                        rec.send_ledgers_to_accounting('transaction_batch', vendor_list)
                        if temp_post:
                            temp_post += ',transaction_batch'
                        else:
                            temp_post += 'transaction_batch'
                        rec.write({
                            'posted_acc_actions': temp_post
                        })
