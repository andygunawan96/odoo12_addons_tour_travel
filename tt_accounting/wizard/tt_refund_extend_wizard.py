from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtRefundExtendWizard(models.TransientModel):
    _name = "tt.refund.extend.wizard"
    _description = 'Refund Extend Wizard'

    refund_id = fields.Many2one('tt.refund', 'Refund', readonly=True)
    new_refund_date = fields.Date('New Refund Date', required=True)

    def extend_refund(self):
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_5'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        refund_obj = self.refund_id
        if self.new_refund_date <= refund_obj.refund_date_ho:
            raise UserError(_("New refund date must be higher than the current one!"))
        else:
            refund_obj.write({
                'refund_date_ho': self.new_refund_date,
                'refund_date': self.new_refund_date
            })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_accounting.tt_refund_action').id
        menu_num = self.env.ref('tt_accounting.menu_transaction_refund').id
        return {
            'type': 'ir.actions.act_url',
            'name': refund_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(refund_obj.id) + "&action=" + str(action_num) + "&model=tt.refund&view_type=form&menu_id=" + str(menu_num),
        }

