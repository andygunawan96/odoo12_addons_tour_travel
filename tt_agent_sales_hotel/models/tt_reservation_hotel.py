from odoo import models,api,fields


class ReservationHotel(models.Model):
    _inherit = 'tt.reservation.hotel'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice')
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')
    invoice_names = fields.Char('Invoice Names', compute='get_invoice_names')

    def get_invoice_names(self):
        name = ""
        for rec in self.invoice_line_ids:
            name = name and "%s~%s" % (name, rec.name_inv) or rec.name_inv
        self.invoice_names = name

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

    def get_segment_description(self):
        tmp = ''
        for rec in self.room_detail_ids:
            tmp += 'Hotel : %s;\n Room  : %s %s(%s),\n' % (self.hotel_name, rec.room_name, rec.room_type, rec.meal_type if rec.meal_type else 'Room Only')
            tmp += 'Date  : %s - %s\n ' % (str(self.checkin_date)[:10], str(self.checkout_date)[:10])
            if rec.special_request:
                tmp += 'Special Request: ' + rec.special_request + '\n'
        return tmp

    def action_create_invoice(self):
        invoice_id = self.env['tt.agent.invoice'].search([('contact_id','=',self.contact_id.id), ('state','=','draft')])
        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'agent_id': self.agent_id.id,
                'contact_id': self.contact_id.id,
                'customer_parent_id': self.customer_parent_id.id,
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': self.get_segment_description(),
        })

        for room_obj in self.room_detail_ids:
            for rec in room_obj.room_date_ids:
                meal = room_obj.meal_type or 'Room Only'
                self.env['tt.agent.invoice.line.detail'].create({
                    'desc': room_obj.room_name + ' (' + meal + ') ' + str(rec.date)[:10],
                    'invoice_line_id': inv_line_obj.id,
                    'price_unit': rec.sale_price,
                    'discount': 0,
                    'quantity': 1,
                })