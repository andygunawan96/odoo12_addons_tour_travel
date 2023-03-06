from odoo import fields,api,models
import json,traceback,logging
from ...tools import ERR, util
from ...tools.ERR import RequestException
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtCustomerParent(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.parent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer Parent'

    name = fields.Char('Name', required=True, default="PT.")
    logo = fields.Binary('Customer Logo')

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', required=True)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent', required=True)  # , default=lambda self: self.env.user.agent_id

    balance = fields.Monetary(string="Balance")
    actual_balance = fields.Monetary(string="Actual Balance", readonly=True, compute="_compute_actual_balance")
    credit_limit = fields.Monetary(string="Credit Limit")
    unprocessed_amount = fields.Monetary(string="Unprocessed Amount", readonly=True, compute="_compute_unprocessed_amount")
    limit_usage_notif = fields.Integer(string="Limit Usage Notification (%)", default=60, help="Send Email Notification when credit limit usage reaches certain percentage.")

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    email = fields.Char(string="Email")
    email_cc = fields.Char(string="Email CC(s) (Split by comma for multiple CCs)", required=False)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    address_ids = fields.One2many('address.detail', 'customer_parent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'customer_parent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'customer_parent_id', 'Social Media')
    customer_ids = fields.Many2many('tt.customer', 'tt_customer_customer_parent_rel','customer_parent_id','customer_id','Customer')
    # booker_ids = fields.Many2many('tt.customer', 'tt_customer_booker_customer_parent_rel', 'customer_parent_id','customer_id', 'Booker')
    booker_customer_ids = fields.One2many('tt.customer.parent.booker.rel', 'customer_parent_id', 'Booker')
    job_hierarchy_ids = fields.One2many('tt.customer.job.hierarchy', 'customer_parent_id', 'Job Hierarchy')
    job_position_ids = fields.One2many('tt.customer.job.position', 'customer_parent_id', 'Job Positions')
    user_ids = fields.One2many('res.users', 'customer_parent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    osi_corporate_code_ids = fields.One2many('tt.osi.corporate.code', 'customer_parent_id', 'OSI Codes')
    tac = fields.Text('Terms and Conditions', readonly=True)
    tax_percentage = fields.Float('Tax (%)', default=0)
    tax_identity_number = fields.Char('NPWP')
    company_bank_data = fields.Char('Company Bank Data')
    is_send_email_cc = fields.Boolean('Send Email to Parent Agent', default=False)

    active = fields.Boolean('Active', default='True')
    state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirmed'),('request', 'Requested'),('validate', 'Validated'),('done', 'Done'),('reject', 'Rejected')], 'State', default='draft', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    confirm_date = fields.Datetime('Confirmed Date', readonly=True)
    request_uid = fields.Many2one('res.users', 'Requested by', readonly=True)
    request_date = fields.Datetime('Requested Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    validate_date = fields.Datetime('Validated Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    done_date = fields.Datetime('Approved Date', readonly=True)
    reject_uid = fields.Many2one('res.users', 'Rejected by', readonly=True)
    reject_date = fields.Datetime('Rejected Date', readonly=True)

    def _compute_unprocessed_amount(self):
        for rec in self:
            total_amt = 0
            invoice_objs = self.env['tt.agent.invoice'].sudo().search([('customer_parent_id', '=', rec.id), ('state', 'in', ['draft', 'confirm'])])
            for rec2 in invoice_objs:
                for rec3 in rec2.invoice_line_ids:
                    total_amt += rec3.total_after_tax

            ## check invoice billed tetapi sudah di bayar
            invoice_bill_objs = self.env['tt.agent.invoice'].sudo().search(
                [('customer_parent_id', '=', rec.id), ('state', 'in', ['bill','bill2']), ('paid_amount','>',0)])
            paid_amount = 0
            for billed_invoice in invoice_bill_objs:
                paid_amount += billed_invoice.paid_amount
            rec.unprocessed_amount = total_amt-paid_amount

    def _compute_actual_balance(self):
        for rec in self:
            rec.actual_balance = rec.credit_limit + rec.balance - rec.unprocessed_amount

    @api.model
    def create(self,vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('cust.par')
        return super(TtCustomerParent, self).create(vals_list)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('tt_base.group_customer_parent_level_5'):
            raise UserError('Action failed due to security restriction. Required Customer Parent Level 5 permission.')
        return super(TtCustomerParent, self).unlink()

    # def convert_all_cust_booker_to_new_format(self):
    #     all_cus_par = self.env['tt.customer.parent'].search([('customer_parent_type_id', '!=', self.env.ref('tt_base.customer_type_fpo').id)])
    #     for rec in all_cus_par:
    #         for rec2 in rec.booker_ids:
    #             booker_obj = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id', '=', rec.id), ('customer_id', '=', rec2.id)], limit=1)
    #             if not booker_obj:
    #                 self.env['tt.customer.parent.booker.rel'].create({
    #                     'customer_parent_id': rec.id,
    #                     'customer_id': rec2.id
    #                 })

    def action_create_corporate_user(self):
        vals = {
            'name': 'Create Corporate User Wizard',
            'res_model': 'create.corporate.user.wizard',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_agent_id': self.parent_agent_id.id,
                'default_customer_parent_id': self.id
            },
        }
        return vals

    @api.model
    def customer_parent_action_view_customer(self):
        action = self.env.ref('tt_base.tt_customer_parent_action_view').read()[0]
        action['context'] = {
            'form_view_ref': 'tt_base.tt_customer_parent_form_view_customer',
            'tree_view_ref': 'tt_base.tt_customer_parent_tree_view_customer',
            'default_parent_agent_id': self.env.user.agent_id.id
        }
        action['domain'] = [('parent_agent_id', '=', self.env.user.agent_id.id)]
        return action
        # return {
        #     'name': 'Customer Parent',
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'tt.customer.parent',
        #     'views': [(self.env.ref('tt_base.tt_customer_parent_tree_view_customer').id, 'tree'),
        #               (self.env.ref('tt_base.tt_customer_parent_form_view_customer').id, 'form')],
        #     'context': {
        #         'default_parent_agent_id': self.env.user.agent_id.id
        #     },
        #     'domain': [('parent_agent_id', '=', self.env.user.agent_id.id)]
        # }

    def check_balance_limit_api(self, customer_parent_id, amount):
        partner_obj = self.env['tt.customer.parent']

        if type(customer_parent_id) == str:
            partner_obj = self.env['tt.customer.parent'].search([('seq_id', '=', customer_parent_id)], limit=1)
        elif type(customer_parent_id) == int:
            partner_obj = self.env['tt.customer.parent'].browse(customer_parent_id)

        if not partner_obj:
            return ERR.get_error(1008)
        if not partner_obj.check_balance_limit(amount):
            return ERR.get_error(1007)
        else:
            return ERR.get_no_error()

    def check_balance_limit(self, amount):
        if not self.ensure_one():
            raise UserError('Can only check 1 agent each time got ' + str(len(self._ids)) + ' Records instead')
        return self.actual_balance >= (amount + (amount * self.tax_percentage / 100))

    def check_send_email_cc(self):
        email_cc = False
        email_cc_list = []
        if self.email_cc:
            email_cc_list += self.email_cc.split(",")
        if self.is_send_email_cc:
            if self.parent_agent_id.email:
                email_cc_list.append(self.parent_agent_id.email)
            if self.parent_agent_id.email_cc:
                email_cc_list += self.parent_agent_id.email_cc.split(",")
        if email_cc_list:
            email_cc_list = list(set(email_cc_list)) ## remove duplicate
            email_cc = ",".join(email_cc_list)
        return email_cc

    def set_all_cor_por_email_cc(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('base.user_admin').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 47')
        all_cor_por = self.env['tt.customer.parent'].search([('customer_parent_type_id', 'in', [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id])])
        for rec in all_cor_por:
            rec.write({
                'is_send_email_cc': True
            })

    def get_corporate_data_api(self, data, context):
        try:
            cor_data = self.env['tt.customer.parent'].search([('seq_id', '=', data['cp_seq_id'])], limit=1)
            cust_data = self.env['tt.customer'].search([('seq_id', '=', data['c_seq_id'])], limit=1)
            if not cor_data or not cust_data:
                raise RequestException(1024)
            if cor_data[0].parent_agent_id.id != context['co_agent_id']:
                raise RequestException(1022, additional_message="Your agent does not have access to this Customer Parent.")
            if cor_data[0].id not in cust_data[0].customer_parent_ids.ids:
                raise RequestException(1022, additional_message="The Customer you selected is not in the selected Customer Parent customer list.")
            res = {
                'customer_parent_name': cor_data[0].name,
                'customer_parent_id': cor_data[0].id,
                'customer_seq_id': cust_data[0].seq_id,
                'customer_parent_type_name': cor_data[0].customer_parent_type_id.name,
                'customer_parent_type_code': cor_data[0].customer_parent_type_id.code
            }
            booker_obj = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id', '=', cor_data[0].id), ('customer_id', '=', cust_data[0].id)], limit=1)
            if booker_obj:
                if booker_obj.job_position_id:
                    booker_job = booker_obj.job_position_id
                    res.update({
                        'job_position_name': booker_job.name,
                        'job_position_sequence': booker_job.sequence,
                        'job_position_is_request_required': booker_job.is_request_required,
                        'job_position_carrier_access_type': booker_job.carrier_access_type,
                        'job_position_carrier_list': booker_job.get_carrier_code_list(),
                        'job_position_currency_code': booker_job.currency_id.name,
                        'job_position_max_price': booker_job.max_price,
                        'job_position_max_hotel_stars': booker_job.max_hotel_stars,
                        'job_position_max_cabin_class': booker_job.max_cabin_class
                    })
                    if booker_job.hierarchy_id:
                        res.update({
                            'hierarchy_sequence': booker_job.hierarchy_id.sequence,
                            'hierarchy_min_approve_amt': booker_job.hierarchy_id.min_approve_amt,
                        })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def action_confirm(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_finance').id, self.env.ref('tt_base.group_tt_agent_user').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 48')
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")
        if not self.address_ids or not self.phone_ids:
            raise UserError("Please fill at least one ADDRESS data and one PHONE data!")
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now()
        })

    def action_request(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 49')
        if self.state != 'confirm':
            raise UserError("Cannot Submit Request because state is not 'confirm'.")

        self.write({
            'state': 'request',
            'request_uid': self.env.user.id,
            'request_date': datetime.now()
        })

    def action_validate(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 50')
        if self.state != 'request':
            raise UserError("Cannot Validate because state is not 'request'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    def set_to_validate(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 51')
        self.write({
            'state': 'validate',
        })

    def action_done(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 52')
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'validate'.")

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def action_reject(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_user').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 53')
        if self.state == 'done':
            raise UserError("Cannot reject already approved Customer Parent.")

        self.write({
            'state': 'reject',
            'reject_uid': self.env.user.id,
            'reject_date': datetime.now()
        })

    def set_to_done(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 54')
        self.write({
            'state': 'done',
        })

    def set_to_draft(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_tt_agent_user').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 55')
        if self.state != 'reject':
            raise UserError("Please reject this Customer Parent before setting it to draft!")

        self.write({
            'state': 'draft',
        })

    #ledger history
    #booking History

    def check_credit_limit_usage(self):
        current_perc = self.actual_balance / self.credit_limit * 100
        if 100-current_perc >= self.limit_usage_notif:
            return 'You have used more than %s percent of your credit limit. Remaining Credit: %s %s / %s %s' % (self.limit_usage_notif, self.currency_id.name,
                                                                                                                 util.get_rupiah(self.actual_balance), self.currency_id.name,
                                                                                                                 util.get_rupiah(self.credit_limit))
        else:
            return 'Remaining Credit: %s %s / %s %s' % (self.currency_id.name, util.get_rupiah(self.actual_balance), self.currency_id.name, util.get_rupiah(self.credit_limit))
