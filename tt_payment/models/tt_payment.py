from odoo import fields, api, models
from odoo import exceptions
from odoo.exceptions import UserError
from datetime import datetime


class PaymentTransaction(models.Model):
    _name = 'tt.payment'
    _rec_name = 'display_name'
    _inherit = 'tt.history'
    _description = 'Payment Model'
    _order = 'id desc'

    name = fields.Char('Name', default='New', help='Sequence number set on Confirm state example:PAY.XXX',readonly=True)
    fee = fields.Monetary('Fee', help='Third party fee',readonly=True, compute="_compute_fee_payment", states={'draft': [('readonly', False)]}) # g dihitung sebagai uang yg bisa digunakan
    loss_or_profit = fields.Monetary('Loss or Profit', readonly=True, compute="_compute_fee_payment", states={'draft': [('readonly', False)]})

    used_amount = fields.Monetary('Used Amount',readonly=True, compute="compute_available_amount")#yang sudah dipakai membayar
    available_amount = fields.Monetary('Available Amount', compute="compute_available_amount",
                                       help='payment amount + unique amount',readonly=True) #nominal yg bisa digunakan

    display_name = fields.Char('Display Name',compute="_compute_display_name_payment",store=False,readonly=True)

    payment_date = fields.Datetime('Payment Date', states={'validated': [('readonly', True)], 'validated2': [('readonly', True)], 'approved': [('readonly', True)]},copy=False)

    real_total_amount = fields.Monetary('Adjusting Amount',help='To edit total when real payment done by customer is different.', states={'validated': [('readonly', True)], 'validated2': [('readonly', True)], 'approved': [('readonly', True)]})
    total_amount = fields.Monetary('Total Payment', required=True, related="real_total_amount") # yang benar benar di transfer
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id,readonly=True)

    top_up_id = fields.Many2one('tt.top.up',"Top Up",readonly=True,copy=False)

    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('validated','Validated by Operator'),
                              ('validated2','Validated by Supervisor'),
                              ('approved','Approved'),
                              ('cancel','Cancelled')], 'State', default='draft', help='Draft: New payment can be edited,'
                                                                                      'Confirm: Agent Confirmed the payment'                                                                                  'Validate by Operator'
                                                                                      'Validate by Supervisor')

    payment_image_ids = fields.Many2many('tt.upload.center','rel_test_image','payment_id','image_id','Image IDs',copy=False)

    adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',domain=[('res_model','=','tt.payment')], readonly=True,copy=False)

    def unlink_image(self):
        self.payment_image_id.unlink()

    def unlink_image_ids(self):
        self.payment_image_ids[0].unlink()

    # Tambahan
    confirm_uid = fields.Many2one('res.users', 'Confirm by',readonly=True)
    confirm_date = fields.Datetime('Confirm Date',readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validate by',readonly=True)
    validate_date = fields.Datetime('Validate Date',readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approve by',readonly=True)
    approve_date = fields.Datetime('Approve Date',readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel By',readonly=True)
    cancel_date = fields.Datetime('Cancel Date',readonly=True)
    reference = fields.Char('Validate Ref.', help='Transaction Reference / Approval number', states={'validated': [('readonly', True)], 'validated2': [('readonly', True)], 'approved': [('readonly', True)]})

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,readonly=True,states={'draft': [('readonly', False)]})
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer',readonly=True,states={'draft': [('readonly', False)]}, domain="[('parent_agent_id', '=', agent_id)]")
    # acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', domain=_get_acquirer_domain,states={'validated': [('readonly', True)]})

    is_full = fields.Boolean('Is Full')

    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer',
                                  states={'validated': [('readonly', True)],
                                          'validated2': [('readonly', True)],
                                          'approved': [('readonly', True)]},
                                  domain="[('agent_id','=',agent_id)]")
    payment_acq_number_id = fields.Many2one('payment.acquirer.number', 'Payment Acquirer Number', readonly=True)

    # #Todo:
    # # 1. Pertimbangkan penggunaan monetary field untuk integer field (pertimbangkan multi currency juga)
    # # 2. Tambahkan confirm uid + confirm date dan validate uid + validate date
    # # 3. Reference => Catat nomor transfer atau detail2x laine
    # # 4. Nama diberikan waktu state draft (karena?) usul klo isa waktu state confirm
    # # 5. Ganti payment_uid dengan agent_id
    # # 6. Tambahkan Payment Acquirer metode pembayaran e

    @api.onchange('agent_id')
    def _onchange_agent(self):
        if self.customer_parent_id.parent_agent_id.id != self.agent_id.id:
            self.customer_parent_id= False
        self.acquirer_id = False

    @api.onchange('customer_parent_id')
    def _onchange_agent_customer_parent(self):
        self.acquirer_id = False

    def _compute_fee_payment(self):
        for rec in self:
            if rec.sudo().acquirer_id:
                loss_or_profit,fee,unique = rec.sudo().acquirer_id.compute_fee(rec.real_total_amount)
                rec.fee = fee
                rec.loss_or_profit = loss_or_profit

    def test_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 71')
        self.write({
            'state': 'draft'
        })

    def test_set_as_confirm(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_payment_level_4').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 72')
        self.write({
            'state': 'confirm'
        })

    # @api.onchange('real_total_amount','acquirer_id')
    # def _onchange_adj_validator(self):
    #     print('onchange')
    #     if self.create_date:
    #         if datetime.datetime.now().day == self.create_date.day:
    #             raise exceptions.UserError('Cannot change, have to wait 1 day.')

    def check_full(self):
        if self.available_amount <= 0:
            self.is_full = True
        else:
            self.is_full = False

    @api.multi
    def compute_available_amount(self):
        for rec in self:
            available_amount = rec.total_amount
            rec.used_amount = 0
            if rec.top_up_id:
                rec.used_amount = self.top_up_id.total
                available_amount = 0
            else:
                available_amount -= rec.used_amount
            rec.available_amount = available_amount

    @api.multi
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

    @api.multi
    def write(self, vals_list):
        if 'real_total_amount' in vals_list:
            if vals_list['real_total_amount'] < self.used_amount and not self.top_up_id:
                raise exceptions.UserError("Total amount on %s is less than the used amount." % (self.name))
        return super(PaymentTransaction, self).write(vals_list)

    def get_is_ho_invoice_payment(self):
        return False

    def action_validate_from_button(self):
        # khusus top up dan HO invoice, agent user tidak boleh klik
        if (self.top_up_id or self.get_is_ho_invoice_payment()) and self.env.user.has_group('tt_base.group_tt_agent_user'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 73b')
        # level 4 = untuk HO yang punya level 4, agent finance = untuk finance agent user
        if not ({self.env.ref('tt_base.group_payment_level_4').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 73')
        if self.state != 'confirm':
            raise exceptions.UserError('%s Can only validate [Confirmed] state Payment.' % (self.name))
        if self.reference:
            if self.top_up_id:
                self.top_up_id.action_validate_top_up(self.total_amount)
            self.action_validate_payment()
        else:
            raise exceptions.UserError('Please write down the payment reference.')

    def action_approve_from_button(self):
        # khusus top up dan HO invoice, agent user tidak boleh klik
        if (self.top_up_id or self.get_is_ho_invoice_payment()) and self.env.user.has_group('tt_base.group_tt_agent_user'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 74b')
        # level 4 = untuk HO yang punya level 4, agent finance = untuk finance agent user
        if not ({self.env.ref('tt_base.group_payment_level_4').id,self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 74')
        if self.state != 'validated':
            raise exceptions.UserError('%s Can only approve [Validated] state Payment.' % (self.name))
        if self.top_up_id:
            ## 3 Januari 2020 di minta hapuskan by desy
            # if self.top_up_id.total != self.real_total_amount and datetime.now().day == self.create_date.day:
            #     raise exceptions.UserError('Cannot change, have to wait 1 day.')
            self.top_up_id.action_approve_top_up()
        self.action_approve_payment()

    def action_approve_payment(self):
        approve_values = {
            'state': 'approved',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        }
        if not self.payment_date:
            approve_values.update({
                'payment_date': datetime.now()
            })
        self.write(approve_values)

    def action_validate_payment(self):
        self.write({
            'state': 'validated',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    def action_cancel_payment(self,context):
        if self.state != 'confirm':
            raise exceptions.UserError('Can only cancel [Confirmed] state Payment.')
        self.write({
            'state': 'cancel',
            'cancel_uid': context.get('co_uid'),
            'cancel_date': datetime.now()
        })

    def action_cancel_from_button(self):
        # khusus top up dan HO invoice, agent user tidak boleh klik
        if (self.top_up_id or self.get_is_ho_invoice_payment()) and self.env.user.has_group('tt_base.group_tt_agent_user'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 75b')
        # level 4 = untuk HO yang punya level 4, agent finance = untuk finance agent user
        if not ({self.env.ref('tt_base.group_payment_level_4').id,self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 75')
        if self.state != 'approved':
            raise exceptions.UserError('Can only cancel [Approved] state Payment.')
        if self.top_up_id:
            raise exceptions.UserError("Cannot cancel top up payment.")
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def action_reject_from_button(self):
        # khusus top up dan HO invoice, agent user tidak boleh klik
        if (self.top_up_id or self.get_is_ho_invoice_payment()) and self.env.user.has_group('tt_base.group_tt_agent_user'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 76b')
        # level 4 = untuk HO yang punya level 4, agent finance = untuk finance agent user
        if not ({self.env.ref('tt_base.group_payment_level_4').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 76')
        self.action_cancel_payment({'co_uid': self.env.user.id})
