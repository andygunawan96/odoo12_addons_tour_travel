from odoo import models, fields, api, _

AMOUNT_TYPE = [
    ('amount', 'Amount'),
    ('percentage', 'Percentage')
]


class AgentRegistrationPromotion(models.Model):
    _name = 'tt.agent.registration.promotion'
    _description = 'Agent Registration Promotion'
    _order = 'sequence desc'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    agent_type_id = fields.Many2one('tt.agent.type', 'Recruit by')
    agent_type_ids = fields.One2many('tt.agent.registration.promotion.agent.type', 'promotion_id', 'Recruited',
                                     help='''Agent Type yang berhak untuk mendapatkan promo.''')
    description = fields.Char('Description')
    default = fields.Boolean('Default Commission')
    sequence = fields.Integer('Sequence')

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        if self.agent_type_id:
            res = '%s - %s' % (self.agent_type_id.code.title(), self.name)
            return res
        else:
            return self.name

    def get_agent_hierarchy(self, agent_id, hierarchy=[]):
        hierarchy.append({
            'agent_id': agent_id.id,
            'agent_name': agent_id.name,
            'agent_type_id': agent_id.agent_type_id.id,
            'code': agent_id.agent_type_id.code,
        })
        if agent_id.parent_agent_id:
            return self.get_agent_hierarchy(agent_id.parent_agent_id, hierarchy)
        else:
            return hierarchy

    def get_commission(self, input_commission, agent_type_id, reference, promotion_id):
        vals_list = []
        remaining_diff = 0

        line_obj = self.env['tt.agent.registration.promotion.agent.type'].search(
            [('promotion_id', '=', promotion_id.id), ('agent_type_id', '=', agent_type_id.id)])
        agent_hierarchy = self.get_agent_hierarchy(reference, hierarchy=[])
        for line in line_obj.line_ids:
            if line.agent_type_id.id == reference.agent_type_id.id:
                vals = {
                    'agent_id': reference.id,
                    'agent_type_id': reference.agent_type_id.id,
                    'amount': line.amount
                }
                vals_list.append(vals)
            else:
                for hierarchy in agent_hierarchy:
                    if hierarchy['agent_type_id'] == line.agent_type_id.id:
                        vals = {
                            'agent_id': hierarchy['agent_id'],
                            'agent_type_id': hierarchy['agent_type_id'],
                            'amount': line.amount
                        }
                        vals_list.append(vals)
        return vals_list


class AgentRegistrationPromotionAgentType(models.Model):
    _name = 'tt.agent.registration.promotion.agent.type'
    _description = 'Agent Registration Promotion Agent Type'

    promotion_id = fields.Many2one('tt.agent.registration.promotion', 'Promotion', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    discount_amount_type = fields.Selection(AMOUNT_TYPE, 'Discount Amount Type')
    discount_amount = fields.Float('Discount Amount')
    preview_price = fields.Monetary('Preview Price', compute='set_preview_price')  # default=0,
    line_ids = fields.One2many('tt.agent.registration.promotion.line', 'res_id', 'Lines')

    @api.depends('agent_type_id', 'discount_amount', 'discount_amount_type')
    @api.onchange('agent_type_id', 'discount_amount', 'discount_amount_type')
    def set_preview_price(self):
        for rec in self:
            if rec.agent_type_id and rec.discount_amount:
                if rec.discount_amount_type:
                    if rec.discount_amount_type == 'amount':
                        rec.preview_price = rec.agent_type_id.registration_fee - rec.discount_amount
                    elif rec.discount_amount_type == 'percentage':
                        rec.preview_price = rec.agent_type_id.registration_fee - (rec.agent_type_id.registration_fee / 100 * rec.discount_amount)
            elif rec.discount_amount == 0:
                rec.preview_price = rec.agent_type_id.registration_fee


class AgentRegistrationPromotionLine(models.Model):
    _name = 'tt.agent.registration.promotion.line'
    _description = 'Agent Registration Promotion Line'

    res_id = fields.Many2one('tt.agent.registration.promotion.agent.type', 'Res ID')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    amount = fields.Monetary('Amount')
