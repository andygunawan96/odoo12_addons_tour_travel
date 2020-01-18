from odoo import models,api,fields
from datetime import date,datetime,timedelta
from odoo.exceptions import UserError
import os, traceback


DAY_TO_INT = {
    'Mon' : -1,
    'Tue' : -2,
    'Wed' : -3,
    'Thu' : -4,
    'Fri' : -5,
    'Sat' : -6,
    'Sun' : -7,
}

class TtBillingCycle(models.Model):
    _name = 'tt.billing.cycle'
    _description = 'Corporate Billing Cycle'

    name = fields.Char('Name', required=True, readonly=True)
    color = fields.Integer('Color Index')
    day = fields.Integer('Weekday in number', readonly=True, required=True,
                                     help='''0 = Daily, -1 = Monday .... -7 = Sunday, 1 = date 1 .... 31 = date 31''')

class TtCustomerParentInh(models.Model):
    _inherit = 'tt.customer.parent'

    billing_cycle_ids = fields.Many2many('tt.billing.cycle', 'customer_parent_billing_cycle_rel', 'customer_parent_id', 'billing_cycle_id',
                                         string='Billing Cycle', help='Days of week to billing process')

    billing_due_date = fields.Integer('Billing Due Date (days)', help='0 = immediate payment, 1 = 1 day after billing creation')

    billing_due_date_ids = fields.Many2many('tt.billing.cycle', 'customer_parent_billing_due_date_rel', 'customer_parent_id',
                                         'billing_cycle_id', domain=[('day', '<', 0)],
                                         string='Billing Due Date', help='Days of week to billing due date')

    @api.model
    def create(self, vals_list):
        if vals_list.get('billing_cycle_ids',[[0,0,0]])[0][2]:
            self.ensure_one_no_billing(vals_list)
        else:
            vals_list['billing_cycle_ids'] = self.default_cycle()
        return super(TtCustomerParentInh, self).create(vals_list)
        
    def write(self, vals):
        self.ensure_one_no_billing(vals)
        super(TtCustomerParentInh, self).write(vals)

    @api.onchange('billing_due_date')
    def _onchange_billing_due_date(self):
        for rec in self:
            if rec.billing_due_date < 0 :
                raise UserError("Cannot go below 0.")

    def ensure_one_no_billing(self,vals):
        if 'billing_cycle_ids' in vals:
            no_billing_id = self.env.ref('tt_billing_statement.billing_cycle_no').id
            if no_billing_id in vals['billing_cycle_ids'][0][2]:
                vals['billing_cycle_ids'][0] = [6,0,[no_billing_id]]

    def default_cycle(self):
        return [(6,0,[self.env.ref('tt_billing_statement.billing_cycle_daily').id])]

    # #might be deprecated
    # def _check_billing_cycle(self,date_param):
    #     ##get COR billing_cyce
    #     cycle_list = []
    #     for cycle in self.billing_cycle_ids:
    #         if cycle.day == 0:
    #             return False
    #         elif cycle.day == 32:
    #             return True
    #         cycle_list.append(cycle.day)
    #     return (DAY_TO_INT[date_param.strftime('%a')] in cycle_list or int(date_param.strftime('%d')) in cycle_list)
    #
    # def test_check_billing_cycle(self):
    #     date_param = date.today()
    #     print(self._check_billing_cycle(date_param))

    def get_billing_due_date(self, bill_due_date, bill_day_list):
        final_due_date = date.today() + timedelta(days=bill_due_date)
        while final_due_date.strftime('%A') not in bill_day_list and bill_day_list:
            final_due_date += timedelta(days=1)
        return final_due_date

    def cron_create_billing_statement(self):
        try:
            ##search for COR billed today
            today_int = date.today().strftime('%d')
            today_str = date.today().strftime('%a')
            cor_list_obj = self.search([('billing_cycle_ids.day','!=','0'), ## not no billing
                                        '|',
                                        '|',
                                        ('billing_cycle_ids.day','=',DAY_TO_INT[today_str]), ## 'mon'
                                        ('billing_cycle_ids.day','=',today_int), # date 1
                                        ('billing_cycle_ids.day','=', 32) # daily
                                       ])

            for cor in cor_list_obj:
                pr = cor.name
                print(pr+ ' : '+','.join([str(rec.name) for rec in cor.billing_cycle_ids]))

                ##search invoice cor tersebut
                invoice_list_obj = self.env['tt.agent.invoice'].search([('customer_parent_id','=',cor.id),('state','in',['draft','confirm'])])
                invoice_list = []
                for inv in invoice_list_obj:
                    print(inv.name)
                    if inv.state == 'draft':
                        inv.action_confirm()
                    inv.action_bill2()
                    invoice_list.append([4,inv.id])
                    ##inv.bill

                bill_day_list = []
                for rec in cor.billing_due_date_ids:
                    bill_day_list.append(str(rec.name))

                # create BS
                if invoice_list:
                    new_bs_obj = self.env['tt.billing.statement'].create({
                        'date': datetime.now(),
                        'due_date': self.get_billing_due_date(cor.billing_due_date, bill_day_list),
                        'agent_id': cor.parent_agent_id.id,
                        'customer_parent_id': cor.id,
                        'invoice_ids': invoice_list,
                        'state': 'confirm'
                    })
        except Exception as e:
            dest = '/var/log/odoo/cron_log'
            if not os.path.exists(dest):
                os.mkdir(dest)
            file = open(
                '%s/%s_%s_error.log' % (dest, 'auto billing', datetime.now().strftime('%Y-%m-%d_%H:%M:%S')),
                'w')
            file.write(traceback.format_exc())
            file.close()