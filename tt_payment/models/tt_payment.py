from odoo import fields, api, models
from odoo import exceptions
from datetime import datetime


class PaymentTransaction(models.Model):
    _name = 'tt.payment'
    _rec_name = 'display_name'
    _inherit = 'tt.history'
    _description = 'Rodex Model'
    _order = 'id desc'

    name = fields.Char('Name', default='New', help='Sequence number set on Confirm state example:PAY.XXX',readonly=True)
    fee = fields.Monetary('Fee', help='Third party fee',readonly=True, compute="_compute_fee_payment", states={'draft': [('readonly', False)]}) # g dihitung sebagai uang yg bisa digunakan
    loss_or_profit = fields.Monetary('Loss or Profit', readonly=True, compute="_compute_fee_payment", states={'draft': [('readonly', False)]})

    used_amount = fields.Monetary('Used Amount',readonly=True, compute="compute_available_amount")#yang sudah dipakai membayar
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
                              ('validated2','Validated by Supervisor'),
                              ('approved','Approved'),
                              ('cancel','Cancelled')], 'State', default='draft', help='Draft: New payment can be edited,'
                                                                                      'Confirm: Agent Confirmed the payment'                                                                                  'Validate by Operator'
                                                                                      'Validate by Supervisor')

    payment_image_ids = fields.Many2many('tt.upload.center','rel_test_image','payment_id','image_id','Image IDs')

    adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',domain=[('res_model','=','tt.payment')])

    def unlink_image(self):
        self.payment_image_id.unlink()

    def unlink_image_ids(self):
        self.payment_image_ids[0].unlink()

    def _get_c_parent_domain(self):
        # if self.agent_id:
        #     return [('parent_agent_id','=',self.agent_id.id)]
        # else:
        return "[('parent_agent_id', '=', agent_id)]"

    @api.onchange('agent_id')
    def _onchange_domain_agent_id(self):
        return {'domain': {
            'customer_parent_id': self._get_c_parent_domain()
        }}

    # def _get_acquirer_domain(self):
    #     if self.customer_parent_id:
    #         return "[('agent_id', '=', agent_id)]"
    #     # if self.customer_parent_id:
    #     #     return [('agent_id','=',self.agent_id.id)]
    #     else:
    #         ho_id = self.env.ref('tt_base.rodex_ho').id
    #         return [('agent_id','=', ho_id )]

    @api.onchange('customer_parent_id')
    def _onchange_domain_customer_parent_id(self):
        print("onchange cpid")
        if self.customer_parent_id:
            dom = [('agent_id', '=', self.agent_id.id)]
        else:
            ho_id = self.env.ref('tt_base.rodex_ho').id
            dom = [('agent_id','=', ho_id )]
        print(dom)
        return {
            'domain':{
                'acquirer_id': dom
            }
        }

    # Tambahan
    confirm_uid = fields.Many2one('res.users', 'Confirm by',readonly=True)
    confirm_date = fields.Datetime('Confirm Date',readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validate by',readonly=True)
    validate_date = fields.Datetime('Validate Date',readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approve by',readonly=True)
    approve_date = fields.Datetime('Approve Date',readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel By',readonly=True)
    cancel_date = fields.Datetime('Cancel Date',readonly=True)
    reference = fields.Char('Validate Ref.', help='Transaction Reference / Approval number',states={'validated': [('readonly', True)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,readonly=True,states={'draft': [('readonly', False)]})
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer',readonly=True,states={'draft': [('readonly', False)]}, domain=_get_c_parent_domain)
    # acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', domain=_get_acquirer_domain,states={'validated': [('readonly', True)]})
    dummy_acquirer_field = fields.Boolean('Generate Acquirer List', default=False)

    def get_payment_acquirer_domain(self):
        if self.customer_parent_id:
            dom = self.env['payment.acquirer'].search([('agent_id','=',self.agent_id.id )]).ids
        else:
            ho_id = self.env.ref('tt_base.rodex_ho').id
            dom = self.env['payment.acquirer'].search([('agent_id','=', ho_id )]).ids
        domain = "[('id','in',[%s])]" % (",".join(list(map(str,dom))))
        return domain

    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer',states={'validated': [('readonly', True)]}, domain=[('id', '=', -1)])

    # #Todo:
    # # 1. Pertimbangkan penggunaan monetary field untuk integer field (pertimbangkan multi currency juga)
    # # 2. Tambahkan confirm uid + confirm date dan validate uid + validate date
    # # 3. Reference => Catat nomor transfer atau detail2x laine
    # # 4. Nama diberikan waktu state draft (karena?) usul klo isa waktu state confirm
    # # 5. Ganti payment_uid dengan agent_id
    # # 6. Tambahkan Payment Acquirer metode pembayaran e


    @api.depends('customer_parent_id', 'agent_id', 'dummy_acquirer_field')
    @api.onchange('customer_parent_id', 'agent_id', 'dummy_acquirer_field')
    def _onchange_domain_payment_acquirer(self):
        return {'domain': {
            'acquirer_id': self.get_payment_acquirer_domain()
        }}

    def _compute_fee_payment(self):
        for rec in self:
            if rec.acquirer_id:
                loss_or_profit,fee,unique = rec.acquirer_id.compute_fee(rec.real_total_amount)
                rec.fee = fee
                rec.loss_or_profit = loss_or_profit

    def test_set_as_draft(self):
        self.write({
            'state': 'draft'
        })

    def test_set_as_confirm(self):
        self.write({
            'state': 'confirm'
        })

    # @api.onchange('real_total_amount','acquirer_id')
    # def _onchange_adj_validator(self):
    #     print('onchange')
    #     if self.create_date:
    #         if datetime.datetime.now().day == self.create_date.day:
    #             raise exceptions.UserError('Cannot change, have to wait 1 day.')

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
            print("Supered Used Amount %d" % (rec.used_amount))
            print("Supered Availale Amount %d" % (rec.available_amount))

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

    @api.multi
    def write(self, vals_list):
        vals_list.update({
            'dummy_acquirer_field': False
        })
        return super(PaymentTransaction, self).write(vals_list)

    def action_validate_from_button(self):
        if self.state != 'confirm':
            raise exceptions.UserError('Can only validate [Confirmed] state Payment.')
        if self.reference:
            if self.top_up_id:
                if ({self.env.ref('tt_base.group_tt_tour_travel_operator').id,
                     self.env.ref('tt_base.group_tt_accounting_operator').id}.intersection(set(self.env.user.groups_id.ids))):
                    self.top_up_id.action_validate_top_up(self.total_amount)
                    self.action_validate_payment()
                else:
                    raise exceptions.UserError('No permission to validate Top Up.')
            else:
                self.action_validate_payment()
        else:
            raise exceptions.UserError('Please write down the payment reference.')

    def action_approve_from_button(self):
        if self.state != 'validated':
            raise exceptions.UserError('Can only validate [Validated] state Payment.')
        if self.top_up_id:
            if ({self.env.ref('tt_base.group_tt_tour_travel_operator').id,
                 self.env.ref('tt_base.group_tt_accounting_operator').id}.intersection(
                set(self.env.user.groups_id.ids))):
                ## 3 Januari 2020 di minta hapuskan by desy
                # if self.top_up_id.total != self.real_total_amount and datetime.now().day == self.create_date.day:
                #     raise exceptions.UserError('Cannot change, have to wait 1 day.')
                self.top_up_id.action_approve_top_up()
                self.action_approve_payment()
            else:
                raise exceptions.UserError('No permission to approve Top Up.')
        else:
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

    def action_reject_from_button(self):
        self.action_cancel_payment({'co_uid': self.env.user.id})

