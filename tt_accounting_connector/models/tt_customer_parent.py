from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging,traceback
from ...tools import util,ERR
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtCustomerParentInhAcc(models.Model):
    _inherit = 'tt.customer.parent'

    def sync_customer_accounting(self, func_action, vendor_list):
        try:
            res = []
            if self.ho_id:
                ho_obj = self.ho_id
            else:
                ho_obj = self.parent_agent_id.ho_id
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
            _logger.info("Failed to create customer data in accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)

    @api.model
    def create(self, vals_list):
        res = super(TtCustomerParentInhAcc, self).create(vals_list)
        if res.customer_parent_type_id.id == self.env.ref('tt_base.customer_type_fpo').id and res.parent_agent_id and res.parent_agent_id.is_sync_to_acc:
            search_params = [('is_create_customer', '=', True)]
            if res.ho_id:
                ho_obj = res.ho_id
            else:
                ho_obj = res.parent_agent_id.ho_id
            if ho_obj:
                search_params.append(('ho_id', '=', ho_obj.id))
            setup_list = self.env['tt.accounting.setup'].search(search_params)
            if setup_list:
                vendor_list = [rec.accounting_provider for rec in setup_list]
                res.sync_customer_accounting('create', vendor_list)
        return res

    def action_done(self):
        super(TtCustomerParentInhAcc, self).action_done()
        if not self.accounting_uid and self.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and self.parent_agent_id and self.parent_agent_id.is_sync_to_acc:
            search_params = [('is_create_customer', '=', True)]
            if self.ho_id:
                ho_obj = self.ho_id
            else:
                ho_obj = self.parent_agent_id.ho_id
            if ho_obj:
                search_params.append(('ho_id', '=', ho_obj.id))
            setup_list = self.env['tt.accounting.setup'].search(search_params)
            if setup_list:
                vendor_list = [rec.accounting_provider for rec in setup_list]
                self.sync_customer_accounting('create', vendor_list)

    def check_use_ext_credit_limit(self):
        return self.parent_agent_id.is_use_ext_credit_cor

    def get_external_credit_limit(self):
        try:
            search_params = []
            if self.ho_id:
                ho_obj = self.ho_id
            else:
                ho_obj = self.parent_agent_id.ho_id
            if ho_obj:
                search_params.append(('ho_id', '=', ho_obj.id))
            setup_list = self.env['tt.accounting.setup'].search(search_params)
            if setup_list and setup_list[0].accounting_provider:
                acc_vendor = setup_list[0].accounting_provider
                vals = {
                    'customer_id': self.accounting_uid,
                    'ho_id': ho_obj.id
                }
                ext_credit_limit = self.env['tt.accounting.connector.%s' % acc_vendor].check_credit_limit(vals)
                ext_credit_limit = float(ext_credit_limit)
                _logger.info('Current external credit limit for customer parent %s is %s' % (self.name, str(ext_credit_limit)))
            else:
                ext_credit_limit = 0
                _logger.info('Accounting Setup not found, failed to check external credit limit for customer parent: %s.' % self.name)
        except Exception as e:
            _logger.error(traceback.format_exc())
            ext_credit_limit = 0
        return ext_credit_limit

    def get_external_payment_acq_seq_id(self):
        if self.parent_agent_id.ext_credit_cor_acq_id:
            return self.parent_agent_id.ext_credit_cor_acq_id.seq_id
        else:
            return self.seq_id
