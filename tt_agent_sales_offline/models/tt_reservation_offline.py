from odoo import models, fields, api, _
from datetime import datetime, timedelta
import base64


class ReservationOffline(models.Model):

    _inherit = 'tt.reservation.offline'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True)  # , compute='set_agent_invoice_state'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.offline')])

    @api.depends('invoice_line_ids')
    def set_agent_invoice_state(self):

        states = []

        for rec in self.invoice_line_ids:
            states.append(rec.state)

        if all(state == 'draft' for state in states) or not states:
            self.state_invoice = 'wait'
        elif all(state != 'draft' for state in states):
            self.state_invoice = 'full'
        elif any(state != 'draft' for state in states):
            self.state_invoice = 'partial'

    def action_create_invoice(self):
        invoice_id = False

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'state': 'confirm',
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'confirmed_date': datetime.now()
            })
            if self.issued_uid.agent_id.id == self.agent_id.id:
                invoice_id.write({
                    'confirmed_uid': self.issued_uid.id
                })
            else:
                invoice_id.write({
                    'confirmed_uid': self.confirm_uid.id
                })

        line_desc = ''
        if self.provider_type_id_name != 'hotel':
            for line in self.line_ids:
                line_desc += line.get_line_description()
        else:
            line_desc += 'Description : ' + (self.description if self.description else '')

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': line_desc,
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        model_type_id = self.env['tt.provider.type'].search([('code', '=', self.offline_provider_type)], limit=1)
        inv_line_obj.write({
            'model_type_id': model_type_id.id
        })

        invoice_line_id = inv_line_obj.id

        # get charge code name

        # get prices

        if self.provider_type_id_name == 'hotel':
            qty = 0
            for line in self.line_ids:
                qty += line.obj_qty
            for line in self.line_ids:
                desc_text = line.get_line_hotel_description()
                inv_line_obj.write({
                    'invoice_line_detail_ids': [(0, 0, {
                        'desc': desc_text,
                        'price_unit': self.total / qty,
                        'quantity': qty,
                        'invoice_line_id': invoice_line_id,
                    })]
                })
        else:
            for psg in self.passenger_ids:
                desc_text = psg.customer_id.name
                price_unit = 0
                for srvc in self.sale_service_charge_ids:
                    if srvc.charge_type not in ['RAC', 'DISC']:
                        price_unit += srvc.amount

                inv_line_obj.write({
                    'invoice_line_detail_ids': [(0, 0, {
                        'desc': desc_text,
                        'price_unit': self.total / len(self.passenger_ids),
                        'quantity': 1,
                        'invoice_line_id': invoice_line_id,
                    })]
                })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': self.customer_parent_id.id,
            'confirm_uid': invoice_id.confirmed_uid.id,
            'confirm_date': datetime.now()
        })
        if self.acquirer_id:
            payment_obj.update({
                'acquirer_id': self.acquirer_id.id,
            })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

    def action_done(self):
        super(ReservationOffline, self).action_done()
        self.action_create_invoice()
