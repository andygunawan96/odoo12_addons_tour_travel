from odoo import api, models, fields
from odoo.exceptions import UserError

from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging,traceback
from ...tools import ERR
import pytz

_logger = logging.getLogger(__name__)



class TtPointReward(models.Model):
    _name = "tt.point.reward"
    _inherit = 'tt.history'
    _description = 'Point Reward Model'
    _rec_name = 'name'
    _order = "sequence asc"

    def _compute_get_ho_id(self):
        if self.env.user.ho_id:
            return self.env.user.ho_id.id
        if self.env.user.agent_id:
            return self.env.user.agent_id.ho_id.id
        return False

    name = fields.Char("Point Reward Name", required=True, default='Point Reward')
    is_active = fields.Boolean('Is Active', default=True)
    agent_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Agent Type Access Type', default='all')
    point_reward_agent_type_eligibility_ids = fields.Many2many("tt.agent.type", "tt_agent_type_tt_point_reward_rel", "tt_point_reward_id", "tt_agent_type_id", "Agent Type")  #type of agent that are able to use the voucher
    provider_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Type Access Type', default='all')
    point_reward_provider_type_eligibility_ids = fields.Many2many("tt.provider.type", "tt_provider_type_tt_point_reward_rel","tt_point_reward_id", "tt_provider_type_id", "Provider Type")  # what product this voucher can be applied
    provider_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Access Type', default='all')
    point_reward_provider_eligibility_ids = fields.Many2many('tt.provider', "tt_provider_tt_point_reward_rel", "tt_point_reward_id","tt_provier_id", "Provider ID")  # what provider this voucher can be applied
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)], default=_compute_get_ho_id)
    point_reward_rules_id = fields.Many2one('tt.point.reward.rules', 'Point Reward Rules', domain='[("ho_id", "=", ho_id)]')
    sequence = fields.Integer('Sequence')

    @api.model
    def create(self, vals_list):
        try:
            if vals_list['sequence'] == None:
                vals_list['sequence'] = len(self.search([])) + 1
        except:
            pass
        return super(TtPointReward, self).create(vals_list)

    def add_point_reward(self, reservation_obj, total_price, co_uid):
        if not reservation_obj.is_get_point_reward:
            ho_agent_obj = reservation_obj.agent_id.ho_id
            try:
                total_point = 0
                ## check agent type yg sesuai
                point_reward_data_obj = self.search([('is_active','=', True), ('ho_id','=', ho_agent_obj.id)])
                for rec in point_reward_data_obj:
                    is_agent_type = False
                    is_provider_type = False
                    is_provider = False
                    if rec.agent_type_access_type == 'all':
                        is_agent_type = True
                    elif rec.agent_type_access_type == 'allow' and list(set(rec.point_reward_agent_type_eligibility_ids.ids) & set([reservation_obj.agent_type_id.id])):
                        is_agent_type = True
                    elif rec.agent_type_access_type == 'restrict' and len(set(rec.point_reward_agent_type_eligibility_ids.ids).intersection([reservation_obj.agent_type_id.id])) == 0:
                        is_agent_type = True

                    if rec.provider_type_access_type == 'all':
                        is_provider_type = True
                    elif rec.provider_type_access_type == 'allow' and list(set(rec.point_reward_provider_type_eligibility_ids.ids) & set([reservation_obj.agent_type_id.id])):
                        is_provider_type = True
                    elif rec.provider_type_access_type == 'restrict' and len(set(rec.point_reward_provider_type_eligibility_ids.ids).intersection([reservation_obj.agent_type_id.id])) == 0:
                        is_provider_type = True

                    if rec.provider_access_type == 'all':
                        is_provider = True
                    elif rec.provider_access_type == 'allow' and list(set(rec.point_reward_provider_eligibility_ids.ids) & set([reservation_obj.agent_type_id.id])):
                        is_provider = True
                    elif rec.provider_access_type == 'restrict' and len(set(rec.point_reward_provider_eligibility_ids.ids).intersection([reservation_obj.agent_type_id.id])) == 0:
                        is_provider = True

                    if is_agent_type and is_provider_type and is_provider: ## check total price sesuai
                        if total_price >= rec.point_reward_rules_id.min_price:
                            if rec.point_reward_rules_id.is_gradual_points:
                                total_point = int(total_price/rec.point_reward_rules_id.min_price) * rec.point_reward_rules_id.points
                            else:
                                total_point = rec.point_reward_rules_id.points
                        ## add point to agent
                        if total_point > 0:
                            self.add_points(reservation_obj, total_point, co_uid)
                        ## RULE KETEMU BREAK
                        break
                ## add point reward to agent
                reservation_obj.is_get_point_reward = True
            except Exception as e:
                _logger.error("%s, %s" % (str(e), traceback.format_exc()))
                return ERR.get_error(500, additional_message=str(e))
        return ERR.get_no_error()

    def add_points(self, reservation_obj, points, co_uid):
        self.env['tt.ledger'].create_ledger_vanilla(
            reservation_obj._name,
            reservation_obj.id,
            'Points For reservation %s' % (reservation_obj.name),
            reservation_obj.name,
            10, # Point Reward
            reservation_obj.currency_id.id,
            co_uid,
            reservation_obj.agent_id.id,
            False,
            int(points),
            0,
            'Ledger Points for %s' % reservation_obj.name,
            'point',
            pnr=reservation_obj.pnr,
            date=fields.datetime.now(),
            display_provider_name=reservation_obj.provider_name,
            provider_type_id=reservation_obj.provider_type_id.id,
        )

    def minus_points(self, reason, reservation_obj, points, co_uid):
        self.env['tt.ledger'].create_ledger_vanilla(
            reservation_obj._name,
            reservation_obj.id,
            "%s Points for Ledger %s" % (reason, reservation_obj.name),
            reservation_obj.name,
            11, # Point Used
            reservation_obj.currency_id.id,
            co_uid,
            reservation_obj.agent_id.id,
            False,
            0,
            int(points),
            '%s Points for Ledger %s' % (reason, reservation_obj.name),
            'point',
            pnr=reservation_obj.pnr,
            date=fields.datetime.now(),
            display_provider_name=reservation_obj.provider_name,
            provider_type_id=reservation_obj.provider_type_id.id,
        )
