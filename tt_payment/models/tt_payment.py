from odoo import fields, api, models
from odoo import exceptions
import datetime


class PaymentTransaction(models.Model):
    _name = 'tt.payment'
    _rec_name = 'display_name'
    _description = 'Rodex Model'

    name = fields.Char('Name', default='New', help='Sequence number set on Confirm state example:PAY.XXX')
    fee = fields.Monetary('Fee', help='Third party fee') # g dihitung sebagai uang yg bisa digunakan

    used_amount = fields.Monetary('Used Amount')#yang sudah dipakai membayar
    available_amount = fields.Monetary('Available Amount', compute="compute_available_amount",
                                       help='payment amount + unique amount') #nominal yg bisa digunakan

    display_name = fields.Char('Display Name',compute="_compute_display_name_payment",store=True)

    payment_date = fields.Datetime('Payment Date') #required

    total_amount = fields.Monetary('Total Payment', required=True ) # yang benar benar di transfer
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)

    top_up_id = fields.Many2one('tt.top.up',"Top Up")

    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('validated','Validated by Operator'),
                              ('validated2','Validated by Supervisor')], 'State', default='draft', help='Draft: New payment can be edited,'
                                                                                         'Confirm: Agent Confirmed the payment'
                                                                                         'Validate by Operator'
                                                                                         'Validate by Supervisor')

    # Tambahan
    confirm_uid = fields.Many2one('res.users', 'Confirm by')
    confirm_date = fields.Datetime('Confirm on')
    validate_uid = fields.Many2one('res.users', 'Validate by')
    validate_date = fields.Datetime('Validate on')
    reference = fields.Char('Validate Ref.', help='Transaction Reference / Approval number')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True)  
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer')
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', domain="['|', ('agent_id', '=', agent_id), ('agent_id', '=', False)]")

    # #Todo:
    # # 1. Pertimbangkan penggunaan monetary field untuk integer field (pertimbangkan multi currency juga)
    # # 2. Tambahkan confirm uid + confirm date dan validate uid + validate date
    # # 3. Reference => Catat nomor transfer atau detail2x laine
    # # 4. Nama diberikan waktu state draft (karena?) usul klo isa waktu state confirm
    # # 5. Ganti payment_uid dengan agent_id
    # # 6. Tambahkan Payment Acquirer metode pembayaran e

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
    @api.depends('name','currency_id','available_amount')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name = '%s - %s %s' % (rec.name, rec.currency_id.name , rec.available_amount)

    @api.model
    def create(self, vals_list):
        if 'name' not in vals_list or vals_list['name'] == ('New'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.payment') or ('New')
        vals_list['state'] = 'confirm'
        new_payment = super(PaymentTransaction, self).create(vals_list)
    #     new_payment.calculate_amount()
        return new_payment
    #
    # def write(self, vals):
    #     vals['residual_amount'] = self.get_residual_amount(vals)
    #     super(PaymentTransaction, self).write(vals)

    def action_validate_from_button(self):
        if self.reference:
            self.state = 'validated'
            if self.top_up_id:
                self.top_up_id.action_validate_top_up()
        else:
            raise exceptions.UserError('Please write down the payment reference')