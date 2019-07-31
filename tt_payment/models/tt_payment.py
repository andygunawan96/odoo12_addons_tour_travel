from odoo import fields, api, models, _
import datetime


class PaymentTransaction(models.Model):
    _name = 'tt.payment'
    _rec_name = 'display_name_1'
    
    name = fields.Char('Name', default='New', help='Sequence number set on Confirm state example:PAY.XXX')
    # pay_amount = fields.Monetary('Payment amount', ) # yang bisa dipakai membayar
    # unique_amount = fields.Monetary('Unique Number', help='For validating direct transfer') # dimasukkan ke payment
    fee = fields.Monetary('Fee', help='Third party fee') # g dihitung sebagai uang yg bisa digunakan

    used_amount = fields.Monetary('Used Amount')#yang sudah dipakai membayar
    residual_amount = fields.Monetary('Residual Amount', help='payment amount + unique amount') #nominal yg bisa digunakan

    display_name_1 = fields.Char('Display Name')

    payment_date = fields.Datetime('Payment Date') #required

    total_amount = fields.Monetary('Total Payment', required=True ) # yang benar benar di transfer
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)

    top_up_id = fields.Char('Top Up')

    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('validated','Validated')], 'State', default='draft', help='Draft: New payment can be edited,'
                                                                                         'Confirm: Agent Confirmed the payment'
                                                                                         'Validate: HO Confirmed the payment')

    # Tambahan
    confirm_uid = fields.Many2one('res.users', 'Confirm by')
    confirm_date = fields.Datetime('Confirm on')
    validate_uid = fields.Many2one('res.users', 'Validate by')
    validate_date = fields.Datetime('Validate on')
    reference = fields.Char('Trans. Ref.', help='Transaction Reference / Approval number')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True)  
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', domain="['|', ('agent_id', '=', agent_id), ('agent_id', '=', False)]")

    #Todo:
    # 1. Pertimbangkan penggunaan monetary field untuk integer field (pertimbangkan multi currency juga)
    # 2. Tambahkan confirm uid + confirm date dan validate uid + validate date
    # 3. Reference => Catat nomor transfer atau detail2x laine
    # 4. Nama diberikan waktu state draft (karena?) usul klo isa waktu state confirm
    # 5. Ganti payment_uid dengan agent_id
    # 6. Tambahkan Payment Acquirer metode pembayaran e

    def get_residual_amount(self,vals = {}):
        return vals.get('total_amount',self.total_amount) - \
               vals.get('used_amount',self.used_amount) - \
               vals.get('fee',self.fee)

    def calculate_amount(self):
        self.residual_amount = self.get_residual_amount()

    @api.model
    def create(self, vals_list):
        if 'name' not in vals_list or vals_list['name'] == _('New'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.payment') or _('New')
        new_payment = super(PaymentTransaction, self).create(vals_list)
        new_payment.calculate_amount()
        new_payment.state = 'confirm'
        return new_payment

    def write(self, vals):
        vals['residual_amount'] = self.get_residual_amount(vals)
        vals['display_name_1'] = self.get_display_name(vals)
        super(PaymentTransaction, self).write(vals)

    def get_display_name(self,vals = {}):
        return '%s - %s %s' % (vals.get('name',self.name), self.currency_id.name ,vals.get('residual_amount',self.residual_amount))

    def action_validate_from_button(self):
        self.state = 'validated'