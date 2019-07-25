from odoo import models, fields, api, _


class ReservationOffline(models.Model):

    _inherit = 'tt.reservation.offline'

    # invoice_line_ids = fields.One2many('tt.agent.invoice.line.','res_id_resv', 'Invoice',
    #                               domain="[('res_model_resv','=','self._name'),('res_id_resv','=','self.id')]")

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True)  # , compute='set_agent_invoice_state'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice')

    invoice_names = fields.Char('Invoice Names', compute='_get_invoice_names')

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

    def _get_invoice_names(self):
        name = ""
        for rec in self.invoice_line_ids:
            name = name and "%s~%s" % (name, rec.name_inv) or rec.name_inv
        self.invoice_names = name

    def action_create_invoice(self):
        invoice_id = self.env['tt.agent.invoice'].search(
            [('contact_id', '=', self.contact_id.id), ('state', '=', 'draft')])

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'contact_id': self.contact_id.id,
                'agent_id': self.agent_id.id,
                'sub_agent_id': self.agent_id.id  # self.sub_agent_id.id
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': 'Testing Offline Invoice'
        })

        invoice_line_id = inv_line_obj.id

        # get charge code name

        # get prices
        def get_pax_price():
            res = {
                'ADT': 0,
                'CHD': 0,
                'INF': 0,
            }
            for svrc in self.cost_service_charge_ids:
                if 'r.ac' not in svrc.charge_code:
                    res[svrc.pax_type] += svrc.amount
            return res

        pax_price = get_pax_price()

        for psg in self.passenger_ids:
            desc_text = psg.passenger_id.first_name + ' ' + psg.passenger_id.last_name + ', ' + psg.pax_type

            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': desc_text,
                    'price_unit': pax_price[psg.pax_type],
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })
