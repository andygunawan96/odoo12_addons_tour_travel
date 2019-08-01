from odoo import models,api,fields




class ReservationTrain(models.Model):

    _inherit = 'tt.reservation.airline'

    # invoice_line_ids = fields.One2many('tt.agent.invoice.line.','res_id_resv', 'Invoice',
    #                               domain="[('res_model_resv','=','self._name'),('res_id_resv','=','self.id')]")

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.airline')])


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
            name = name and "%s~%s" % (name,rec.name_inv) or rec.name_inv
        self.invoice_names=name

    invoice_names = fields.Char('Invoice Names', compute=_get_invoice_names)

    def get_segment_description(self):
        tmp = ''
        # vals = []
        for rec in self.segment_ids:
            tmp += '%s(%s) - %s(%s),' % (rec.origin_id.city, rec.origin_id.code, rec.destination_id.city, rec.destination_id.code)
            tmp += '%s - %s\n ' % (rec.departure_date[:16], rec.arrival_date[:16])
            # tmp += rec.carrier_id and rec.carrier_id.name + ' ' or ''
            tmp += rec.carrier_name and rec.carrier_name + '\n' or '\n'
        return tmp

    def action_create_invoice(self):

        invoice_id = self.env['tt.agent.invoice'].search([('contact_id','=',self.contact_id.id), ('state','=','draft')])

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'contact_id': self.contact_id.id,
                'agent_id': self.agent_id.id,
                'sub_agent_id': self.sub_agent_id.id
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': self.get_segment_description()
        })

        invoice_line_id = inv_line_obj.id

        def get_charge_code_name(charge_code):
            if charge_code == 'r.oc':
                return 'Admin fee'
            elif 'r.ac' in charge_code:
                return 'commission'
            elif charge_code == 'disc':
                return 'Discount'
            else:
                return charge_code


        def get_pax_price():
            res = {
                'YCD': 0,
                'ADT': 0,
                'CHD': 0,
                'INF': 0,
                'SSR': 0,
            }
            for svrc in self.sale_service_charge_ids:
                if svrc.charge_type == 'SSR':
                    res['SSR'] += svrc.amount
                elif not 'r.ac' in svrc.charge_code:
                    res[svrc.pax_type] += svrc.amount
            return res

        pax_price = get_pax_price()

        # SSR =
        if pax_price['SSR']:
            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': "SSR",
                    'price_unit': pax_price['SSR'],
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })

        #untuk harga fare per passenger
        for psg in self.passenger_ids:

            #fixme this later
            if int(psg.age) >= 17:
                psg.pax_type = 'ADT'
            else:
                psg.pax_type = 'CHD'

            desc_text = '%s, %s %s' % (' '.join((psg.first_name, psg.last_name)), psg.title, psg.pax_type)

            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': desc_text,
                    'price_unit': pax_price[psg.pax_type],
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })


    # ## CREATED by Samvi 2018/07/24
    @api.multi
    def action_check_provider_state(self, api_context=None):
        res = super(ReservationTrain, self).action_check_provider_state(api_context)
        if self.provider_booking_ids:
            # todo membuat mekanisme untuk partial issued seperti apa
            # fixme sementara create agent invoice berdasarkan bookingan
            if any(rec.state == 'issued' for rec in self.provider_booking_ids):
                # if self.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id,
                #                                       self.env.ref('tt_base_rodex.agent_type_japro').id]:
                self.action_create_invoice()

        return res