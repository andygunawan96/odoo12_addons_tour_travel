from odoo import api,models,fields

class TtAgentInh(models.Model):
    _inherit = 'tt.agent'

    def create_walkin_obj_val(self,new_agent,agent_name):
        val = super(TtAgentInh, self).create_walkin_obj_val(new_agent,agent_name)
        val.update({
            'billing_cycle_ids': [4,self.env.ref('tt_rodex_billing.billing_cycle_no').id]
        })
        return val