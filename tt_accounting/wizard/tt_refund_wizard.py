from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtRefundWizard(models.TransientModel):
    _name = "tt.refund.wizard"
    _description = 'Refund Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)

    booker_id = fields.Many2one('tt.customer', 'Booker', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    service_type = fields.Char('Service Type', required=True, readonly=True)

    refund_type_id = fields.Many2one('tt.refund.type', 'Refund Type', required=True)

    referenced_pnr = fields.Char('Ref. PNR',required=True,readonly=True)
    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)
    referenced_document_external = fields.Char('Ref. Document External',readonly=True) # btbo2

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    def refund_api(self, data, ctx):
        try:
            book_obj = self.env[data['res_model']].search([('name','=',data['referenced_document_external'])], limit=1)
            refund_type_obj = self.env['tt.refund.type'].search([('name','=',data['refund_type_id'])], limit=1)
            provider_type_obj = self.env['tt.provider.type'].search([('name','=',data['provider_type'])], limit=1)
            refund_obj = self.env['tt.refund'].search([('referenced_document','=',data['referenced_document_external']), ('state','!=','cancel')])
            if not refund_obj:
                refund_obj = self.create({
                    'ho_id': ctx['co_ho_id'],
                    'agent_id': ctx['co_agent_id'],
                    'agent_type_id': ctx['co_agent_type_id'],
                    'customer_parent_id': book_obj.customer_parent_id.id,
                    'customer_parent_type_id': book_obj.customer_parent_type_id.id,
                    'booker_id': book_obj.booker_id.id,
                    'currency_id': book_obj.currency_id.id,
                    'service_type': provider_type_obj.id,
                    'refund_type_id': refund_type_obj.id,
                    'referenced_pnr': data['referenced_pnr'],
                    'referenced_document': book_obj.name,
                    'referenced_document_external': data['referenced_document'],
                    'res_model': data['res_model'],
                    'res_id': book_obj.id,
                    'notes': data['notes']
                })
                refund_obj.submit_refund()
            else:
                for rec in refund_obj:
                    rec.referenced_document_external = data['referenced_document'] # update reference doc (mungkin di HO bikin belum ke catat no ref dari BTBO2)
            res = ERR.get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500)
        return res

    def submit_refund(self):
        try:
            book_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        except:
            _logger.info('Warning: Error res_model di production')
            book_obj = self.env[self.env.context['active_model']].sudo().browse(int(self.env.context['active_id']))

        #tembak parent IVAN
        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)], limit=1)
        if resv_obj:
            resv_obj = resv_obj[0]
        else:
            raise UserError('Referenced Document Not Found.')
        total_vendor = len(resv_obj.provider_booking_ids)
        referenced_document_external = ''
        for rec in resv_obj.provider_booking_ids:
            if 'rodextrip' in rec.provider_id.code and not 'rodextrip_other' in rec.provider_id.code:
                #tembak gateway
                data = {
                    'notes': self.notes,
                    'refund_type_id': self.refund_type_id.name,
                    'referenced_document': resv_obj.name,
                    'provider_type': resv_obj.provider_type_id.name,
                    # 'referenced_document_external': 'AL.20120301695',
                    'referenced_document_external': rec.pnr2,
                    'referenced_pnr': rec.pnr,
                    'res_model': self.res_model,
                    'provider': rec.provider_id.code,
                    # 'provider': 'rodextrip_airline',
                    'booking_desc': book_obj.get_aftersales_desc(),
                    'type': 'refund_request_api'
                }
                if referenced_document_external != '':
                    referenced_document_external += ', '
                referenced_document_external = rec.pnr2
                self.env['tt.refund.api.con'].send_refund_request(data, self.agent_id.ho_id.id)
        if referenced_document_external == '':
            referenced_document_external = self.referenced_document_external

        if self.refund_type_id.id == self.env.ref('tt_accounting.refund_type_quick_refund').id:
            ref_type = 'quick'
        else:
            ref_type = 'regular'
        default_adm_fee = self.env['tt.refund'].get_refund_admin_fee_rule(self.agent_id.id, ref_type, provider_type_id=resv_obj.provider_type_id.id)
        refund_obj = self.env['tt.refund'].create({
            'ho_id': self.ho_id.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'booker_id': self.booker_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'refund_type_id': self.refund_type_id.id,
            'admin_fee_id': default_adm_fee.id,
            'referenced_document': self.referenced_document,
            'referenced_pnr': self.referenced_pnr,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'booking_desc': book_obj.get_aftersales_desc(),
            'referenced_document_external': referenced_document_external,
            'notes': self.notes
        })
        refund_line_ids = []
        for pax in book_obj.passenger_ids:
            pax_price = 0
            for cost in pax.cost_service_charge_ids:
                if cost.charge_type != 'RAC':
                    pax_price += cost.amount
            line_obj = self.env['tt.refund.line'].create({
                'name': (pax.title or '') + ' ' + (pax.name or ''),
                'birth_date': pax.birth_date,
                'pax_price': pax_price,
                'total_vendor': total_vendor
            })
            refund_line_ids.append(line_obj.id)
        refund_obj.update({
            'refund_line_ids': [(6, 0, refund_line_ids)],
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
