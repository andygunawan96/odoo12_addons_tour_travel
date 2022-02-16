from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)

class TtSetPnrWizard(models.TransientModel):
    _name = "tt.set.pnr.wizard"
    _description = 'Set PNR Wizard'

    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource',readonly=True)

    pnr = fields.Char('PNR')

    def set_pnr(self):

        provider_obj = self.env['tt.provider.groupbooking'].search([('id','=',self.res_id)])
        provider_obj.update({
            "pnr": self.pnr
        })
        for svc_obj in provider_obj.cost_service_charge_ids:
            svc_obj.update({
                'description': self.pnr
            })
        # for inv_line_obj in provider_obj.booking_id.invoice_line_ids:


        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
