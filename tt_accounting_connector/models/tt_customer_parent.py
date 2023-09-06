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
        if res.parent_agent_id and res.parent_agent_id.is_sync_to_acc:
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
