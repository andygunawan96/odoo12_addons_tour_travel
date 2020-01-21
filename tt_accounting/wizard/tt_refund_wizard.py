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

    booker_id = fields.Many2one('tt.customer', 'Booker', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    service_type = fields.Char('Service Type', required=True, readonly=True)

    refund_type = fields.Selection([('quick', 'Quick Refund (Max. 3 days process)'), ('regular', 'Regular Refund (40 days process)')], 'Refund Type',
                                   required=True, default='regular')

    referenced_pnr = fields.Char('Ref. PNR',required=True,readonly=True)
    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    def submit_refund(self):
        try:
            book_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        except:
            _logger.info('Warning: Error res_model di production')
            book_obj = self.env[self.env.context['active_model']].sudo().browse(int(self.env.context['active_id']))

        refund_obj = self.env['tt.refund'].create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'booker_id': self.booker_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'refund_type': self.refund_type,
            'admin_fee_id': self.refund_type == 'quick' and self.env.ref('tt_accounting.admin_fee_refund_quick').id or self.env.ref('tt_accounting.admin_fee_refund_regular').id,
            'referenced_document': self.referenced_document,
            'referenced_pnr': self.referenced_pnr,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'booking_desc': book_obj.get_aftersales_desc(),
            'notes': self.notes
        })
        for pax in book_obj.passenger_ids:
            pax_price = 0
            for cost in pax.cost_service_charge_ids:
                if cost.charge_type != 'RAC':
                    pax_price += cost.amount
            self.env['tt.refund.line'].create({
                'refund_id': refund_obj.id,
                'name': (pax.title or '') + ' ' + (pax.name or ''),
                'birth_date': pax.birth_date,
                'pax_price': pax_price,
            })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_accounting.tt_refund_action').id
        menu_num = self.env.ref('tt_accounting.menu_transaction_refund').id
        return {
            'type': 'ir.actions.act_url',
            'name': refund_obj.name,
            'target': 'new',
            'url': base_url + "/web#id=" + str(refund_obj.id) + "&action=" + str(action_num) + "&model=tt.refund&view_type=form&menu_id=" + str(menu_num),
        }

