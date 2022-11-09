from odoo import api,models,fields
import pytz, logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DAY_TO_INT = {
    'Mon' : -1,
    'Tue' : -2,
    'Wed' : -3,
    'Thu' : -4,
    'Fri' : -5,
    'Sat' : -6,
    'Sun' : -7,
}

class TtAgentInh(models.Model):
    _inherit = 'tt.agent'

    billing_cycle_ids = fields.Many2many('tt.billing.cycle', 'tt_agent_billing_cycle_rel', 'agent_id',
                                         'billing_cycle_id',
                                         string='Billing Cycle', help='Days of week to billing process')

    billing_due_date = fields.Integer('Billing Due Date (days)', help="How many days until due date after billing.")

    billing_due_date_ids = fields.Many2many('tt.billing.cycle', 'tt_agent_billing_due_date_rel',
                                            'agent_id',
                                            'billing_cycle_id', domain=[('day', '<', 0)],
                                            string='Billing Due Date', help='Days of week to billing due date')

    @api.model
    def create(self, vals_list):
        if vals_list.get('billing_cycle_ids', [[0, 0, 0]])[0][2]:
            self.ensure_one_no_billing(vals_list)
        else:
            vals_list['billing_cycle_ids'] = self.default_cycle()
        return super(TtAgentInh, self).create(vals_list)

    def write(self, vals):
        self.ensure_one_no_billing(vals)
        super(TtAgentInh, self).write(vals)

    @api.onchange('billing_due_date')
    def _onchange_billing_due_date(self):
        for rec in self:
            if rec.billing_due_date < 0:
                raise UserError("Cannot go below 0.")

    def ensure_one_no_billing(self, vals):
        if 'billing_cycle_ids' in vals:
            no_billing_id = self.env.ref('tt_billing_statement.billing_cycle_no').id
            if no_billing_id in vals['billing_cycle_ids'][0][2]:
                vals['billing_cycle_ids'][0] = [6, 0, [no_billing_id]]

    def default_cycle(self):
        return [(6, 0, [self.env.ref('tt_billing_statement.billing_cycle_daily').id])]

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

    def get_billing_due_date(self, today_date, bill_due_date, bill_day_list):
        final_due_date = today_date + timedelta(days=bill_due_date)
        while final_due_date.strftime('%A') not in bill_day_list and bill_day_list:
            final_due_date += timedelta(days=1)
        return final_due_date

    def create_walkin_obj_val(self,new_agent,agent_name):
        val = super(TtAgentInh, self).create_walkin_obj_val(new_agent,agent_name)
        val.update({
            'billing_cycle_ids': [(6,0,[self.env.ref('tt_billing_statement.billing_cycle_no').id])]
        })
        return val


    def cron_create_billing_statement(self):
        ##search for COR billed today
        tz_utc7 = pytz.timezone('Asia/Jakarta')
        today_date = datetime.now(tz_utc7).date()
        today_int = today_date.strftime('%d')
        today_str = today_date.strftime('%a')
        agent_list_obj = self.search([('billing_cycle_ids.day','!=','0'), ## not no billing
                                    '|',
                                    '|',
                                    ('billing_cycle_ids.day','=',DAY_TO_INT[today_str]), ## 'mon'
                                    ('billing_cycle_ids.day','=',today_int), # date 1
                                    ('billing_cycle_ids.day','=', 32) # daily
                                   ])

        for agent_obj in agent_list_obj:
            pr = agent_obj.name
            _logger.info(pr+ ' : '+','.join([str(rec.name) for rec in agent_obj.billing_cycle_ids]))

            ##search invoice cor tersebut
            invoice_list_obj = self.env['tt.ho.invoice'].search([('agent_id','=',agent_obj.id),('state','in',['draft','confirm'])])
            invoice_list = []
            for inv in invoice_list_obj:
                _logger.info(inv.name)
                if inv.state == 'draft':
                    inv.action_confirm()
                if inv.state == 'confirm': ## error billing billed inv. this happen during splitted invoice
                    inv.action_bill2()
                invoice_list.append([4,inv.id])
                ##inv.bill

            bill_day_list = []
            for rec in agent_obj.billing_due_date_ids:
                bill_day_list.append(str(rec.name))

            # create BS
            if invoice_list:
                new_bs_obj = self.env['tt.billing.statement'].create({
                    'date': datetime.now(),
                    'due_date': self.get_billing_due_date(today_date,agent_obj.billing_due_date, bill_day_list),
                    'agent_id': agent_obj.id,
                    'ho_invoice_ids': invoice_list,
                    'state': 'confirm'
                })

                try:
                    if agent_obj.email:
                        mail_created = self.env['tt.email.queue'].sudo().search([('res_id', '=', new_bs_obj.id), ('res_model', '=', new_bs_obj._name), ('type', '=', 'billing_statement')], limit=1)
                        if not mail_created:
                            temp_data = {
                                'provider_type': 'billing_statement',
                                'order_number': new_bs_obj.name,
                            }
                            temp_context = {
                                'co_agent_id': new_bs_obj.agent_id.id
                            }
                            self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                        else:
                            _logger.info('Billing Statement email for {} is already created!'.format(new_bs_obj.name))
                            raise Exception('Billing Statement email for {} is already created!'.format(new_bs_obj.name))
                except Exception as e:
                    _logger.info('Error Create Email Queue from Head Office to %s' % agent_obj.name)
