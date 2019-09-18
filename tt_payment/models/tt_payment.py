from odoo import fields, api, models
from odoo import exceptions
import datetime


class PaymentTransaction(models.Model):
    _name = 'tt.payment'
    _rec_name = 'display_name'
    _description = 'Rodex Model'

    name = fields.Char('Name', default='New', help='Sequence number set on Confirm state example:PAY.XXX',readonly=True)
    fee = fields.Monetary('Fee', help='Third party fee',readonly=True, states={'draft': [('readonly', False)]}) # g dihitung sebagai uang yg bisa digunakan

    used_amount = fields.Monetary('Used Amount',readonly=True)#yang sudah dipakai membayar
    available_amount = fields.Monetary('Available Amount', compute="compute_available_amount",
                                       help='payment amount + unique amount',readonly=True) #nominal yg bisa digunakan

    display_name = fields.Char('Display Name',compute="_compute_display_name_payment",store=True,readonly=True)

    payment_date = fields.Datetime('Payment Date',states={'validated': [('readonly', True)]})

    real_total_amount = fields.Monetary('Adjusting Amount',help='To edit total when real payment done by customer is different.',states={'validated': [('readonly', True)]})
    total_amount = fields.Monetary('Total Payment', required=True, related="real_total_amount") # yang benar benar di transfer
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id,readonly=True)

    top_up_id = fields.Many2one('tt.top.up',"Top Up",readonly=True)

    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('validated','Validated by Operator'),
                              ('validated2','Validated by Supervisor')], 'State', default='draft', help='Draft: New payment can be edited,'
                                                                                         'Confirm: Agent Confirmed the payment'
                                                                                         'Validate by Operator'
                                                                                         'Validate by Supervisor')

    def _get_c_parent_domain(self):
        return [('parent_agent_id','=',self.agent_id.id)]

    @api.onchange('agent_id')
    def _onchange_domain_agent_id(self):
        return {'domain': {
            'customer_parent_id': self._get_c_parent_domain()
        }}

    @api.onchange('customer_parent_id')
    def _onchange_domain_customer_parent_id(self):
        return {'domain': {
            'acquirer_id': [('agent_id','=',self.agent_id.id)]
        }}

    # Tambahan
    confirm_uid = fields.Many2one('res.users', 'Confirm by',readonly=True)
    confirm_date = fields.Datetime('Confirm on',readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validate by',readonly=True)
    validate_date = fields.Datetime('Validate on',readonly=True)
    reference = fields.Char('Validate Ref.', help='Transaction Reference / Approval number',states={'validated': [('readonly', True)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,readonly=True,states={'draft': [('readonly', False)]})
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer',readonly=True,states={'draft': [('readonly', False)]}, domain=_get_c_parent_domain)
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', domain="['|', ('agent_id', '=', agent_id), ('agent_id', '=', False)]",states={'validated': [('readonly', True)]})

    # #Todo:
    # # 1. Pertimbangkan penggunaan monetary field untuk integer field (pertimbangkan multi currency juga)
    # # 2. Tambahkan confirm uid + confirm date dan validate uid + validate date
    # # 3. Reference => Catat nomor transfer atau detail2x laine
    # # 4. Nama diberikan waktu state draft (karena?) usul klo isa waktu state confirm
    # # 5. Ganti payment_uid dengan agent_id
    # # 6. Tambahkan Payment Acquirer metode pembayaran e



    @api.onchange('real_total_amount','acquirer_id')
    def _onchange_adj_validator(self):
        print('onchange')
        if self.create_date:
            if datetime.datetime.now().day == self.create_date.day:
                raise exceptions.UserError('Cannot change, have to wait 1 day.')

    @api.multi
    def compute_available_amount(self):
        for rec in self:
            available_amount = rec.total_amount - rec.fee
            rec.used_amount = 0
            if self.top_up_id:
                rec.used_amount = self.top_up_id.total
            available_amount -= rec.used_amount
            rec.available_amount = available_amount

    @api.multi
    @api.depends('name','currency_id','total_amount')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name = '%s - %s %s' % (rec.name, rec.currency_id.name , rec.available_amount)

    @api.model
    def create(self, vals_list):
        if 'name' not in vals_list or vals_list['name'] == ('New'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.payment') or ('New')
        vals_list['state'] = 'confirm'
        new_payment = super(PaymentTransaction, self).create(vals_list)
        return new_payment

    def action_validate_from_button(self):
        if self.state != 'confirm':
           raise exceptions.UserError('Can only validate [Confirmed] state Payment.')
        if self.reference and self.payment_date:
            if self.top_up_id:
                if ({self.env.ref('tt_base.group_tt_tour_travel_operator'),
                      self.env.ref('tt_base.group_tt_accounting_operator')}.intersection({self.env.user.groups_id.ids})):
                    self.top_up_id.action_validate_top_up(self.total_amount)
                    self.state = 'validated'
                else:
                    raise  exceptions.UserError('No permission to validate Top Up.')
            else:
                self.state = 'validated'
        else:
            raise exceptions.UserError('Please write down the payment reference and payment date.')

