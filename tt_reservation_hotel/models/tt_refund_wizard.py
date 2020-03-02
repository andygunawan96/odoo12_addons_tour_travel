from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtRefundWizard(models.TransientModel):
    _inherit = "tt.refund.wizard"

    def submit_refund(self):
        result = super(TtRefundWizard, self).submit_refund()
        # result = {
        #     'type': 'ir.actions.act_url',
        #     'name': refund_obj.name,
        #     'target': 'self',
        #     'url': base_url + "/web#id=" + str(refund_obj.id) + "&action=" + str(
        #         action_num) + "&model=tt.refund&view_type=form&menu_id=" + str(menu_num),
        # }
        refund_obj = self.env['tt.refund'].search([('name', '=', result['name'])])
        if refund_obj.res_model == 'tt.reservation.hotel':
            if refund_obj.refund_line_ids:
                resv_obj = self.env[refund_obj.res_model].browse(refund_obj.res_id)
                line_obj = refund_obj.refund_line_ids[0]
                line_obj.pax_price = resv_obj.total
        return result
