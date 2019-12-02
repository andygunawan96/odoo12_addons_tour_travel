from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtRefundWizard(models.TransientModel):
    _name = "tt.refund.wizard"
    _description = 'Refund Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)

    currency_id = fields.Many2one('res.currency', readonly=True)
    service_type = fields.Char('Service Type', required=True, readonly=True)

    refund_type = fields.Selection([('quick', 'Quick Refund'), ('regular', 'Regular Refund')], 'Refund Type',
                                   required=True, default='regular')

    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    def submit_refund(self):
        refund_obj = self.env['tt.refund'].create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'refund_type': self.refund_type,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'notes': self.notes
        })

        has_provider = False
        resv_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        ref_id_list = []
        for rec in resv_obj.refund_ids:
            for rec2 in rec.provider_booking_ids:
                ref_id_list.append({
                    'res_model': str(rec2.res_model),
                    'res_id': int(rec2.res_id)
                })
        for rec in resv_obj.provider_booking_ids:
            check_exist = {
                'res_model': str(rec._name),
                'res_id': int(rec.id)
            }
            if rec.state == 'issued' and check_exist not in ref_id_list:
                self.env['tt.provider.refund'].sudo().create({
                    'name': rec.pnr,
                    'res_id': rec.id,
                    'res_model': rec._name,
                    'refund_id': refund_obj.id,
                })
                has_provider = True

        if not has_provider:
            raise UserError("There is no 'Issued' provider available for refund in this reservation!")
