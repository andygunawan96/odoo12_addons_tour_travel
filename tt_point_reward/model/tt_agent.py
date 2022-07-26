from odoo import api, models, fields

from datetime import datetime, date, timedelta
import logging,traceback
import pytz

_logger = logging.getLogger(__name__)



class TtAgent(models.Model):

    _inherit = 'tt.agent'

    point_reward = fields.Monetary(string="Point Reward", compute="_compute_point_reward_agent")

    def _compute_all_point_reward_agent(self):
        for rec in self.search([]):
            rec._compute_point_reward_agent()

    @api.onchange('ledger_ids')
    def _compute_point_reward_agent(self):
        point_reward = 0
        for rec in self:
            if len(rec.ledger_ids)>0:
                for ledger_points_obj in rec.ledger_ids.search([('source_of_funds_type','=',1)]): ## source_of_funds_type 1 untuk points
                    point_reward += ledger_points_obj.debit - ledger_points_obj.credit
            rec.point_reward = point_reward

    # kalau pakai cron sementara tidak di pakai
    def create_point_reward_statement(self):
        statement_ledger_obj = self.env['tt.ledger'].search([('agent_id', '=', self.id), ('transaction_type', '=', 9), ('source_of_funds_type', '=', 1)], limit=1,order='id desc') ## source_of_funds_type 1 untuk points
        dom = [('agent_id', '=', self.id)]
        beginning = True
        if statement_ledger_obj:
            dom.append(('id', '>', statement_ledger_obj.id))
        list_check_ledger_objs = self.env['tt.ledger'].search(dom, order='id asc')
        _logger.info("Agent %s %s ledger since last balance statement" % (self.name, len(list_check_ledger_objs.ids)))
        for idx, ledger in enumerate(list_check_ledger_objs):
            if beginning:
                beginning = False
                continue
            true_balance = list_check_ledger_objs[idx - 1].balance + ledger.debit - ledger.credit
            if ledger.balance != true_balance:
                ledger.balance = true_balance
                _logger.info("Ledger %s ID %s from agent %s Balance Fixed" % (ledger.name, ledger.id, self.name))
        self._compute_point_reward_agent()

        ##create ledger statement
        self.env['tt.ledger'].create_ledger_vanilla(
            self._name,
            self.id,
            'End Balance Statement %s' % (self.name),
            self.seq_id,
            datetime.now(pytz.timezone('Asia/Jakarta')).date(),
            9,
            self.currency_id.id,
            self.env.ref('base.user_root').id,
            self.id,
            False,
            0,
            0,
            'Automatic End Points Statement',
            1
        )


