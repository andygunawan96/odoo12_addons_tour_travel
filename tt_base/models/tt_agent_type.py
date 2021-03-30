from odoo import models, fields, api, _
from ...tools import variables


class TtAgentType(models.Model):
    _name = 'tt.agent.type'
    _inherit = ['tt.history']
    _description = 'Tour & Travel - Agent Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, help='Fixed code, ex: citra, japro, for sale pricing', default='undefine')
    active = fields.Boolean('Active', default='True')
    registration_upline_ids = fields.Many2many('tt.agent.type', 'tt_agent_type_upline_1_2_rel', 'agent_1', 'agent_2')
    description = fields.Text('Description')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    registration_fee = fields.Monetary('Registration Fee')
    benefit = fields.Many2many('tt.agent.type.benefit', 'tt_agent_type_benefit_rel', 'agent_benefit', 'benefit')
    registration_form = fields.Html(string="Registration Form")
    agent_ids = fields.One2many('tt.agent', 'agent_type_id', 'Agent')
    can_register_agent = fields.Boolean('Can Register Agent', default=False)
    can_be_registered = fields.Boolean('Can be Registered', default=False)
    seq_prefix = fields.Char('Sequence Prefix', size=2, required=True)
    terms_and_condition = fields.Html('Terms and Condition')
    is_using_pnr_quota = fields.Boolean('Is Using PNR Quota')
    is_using_invoice = fields.Boolean('Is Using Invoice', default=True)
    is_send_email_issued = fields.Boolean('Is Send Email Issued', default=False)
    is_send_email_booked = fields.Boolean('Is Send Email Booked', default=False)
    menuitem_id = fields.Many2one('ir.ui.menu','Menuitem')
    sequence_prefix_id = fields.Many2one('ir.sequence','Sequence Prefix')
    rounding_amount_type = fields.Selection(selection=variables.ROUNDING_AMOUNT_TYPE, string='Rounding Amount Type', help='Set rounding type amount in pricing', default='round')
    rounding_places = fields.Integer('Rounding Places', default=0)
    user_template_ids = fields.One2many('res.users', 'agent_type_id', 'User Templates', readonly=True)

    @api.model
    def create(self, vals_list):
        new_agent_type = super(TtAgentType, self).create(vals_list)
        sequence_obj = self.env['ir.sequence'].create({
            'name': new_agent_type.name,
            'code': 'tt.agent.type.%s' % (new_agent_type.code),
            'prefix': '{}.%(day)s%(sec)s'.format(new_agent_type.seq_prefix),
            'padding': 3
        })
        new_agent_type.sequence_prefix_id = sequence_obj.id
        new_agent_type.create_menuitem()
        try:
            """ Set registration upline menjadi HO """
            new_agent_type.write({
                'registration_upline_ids': [(4, self.env.ref('tt_base.agent_type_ho').id)],
            })
        except ValueError:
            """ Jika belum ada HO, kosongi """
            pass
        return new_agent_type

    def unlink(self):
        self.delete_menuitem()
        super(TtAgentType, self).unlink()

    def write(self, vals):
        super(TtAgentType, self).write(vals)
        if 'name' in vals:
            self.menuitem_id.name = vals['name']
        if 'code' in vals:
            self.sequence_prefix_id.code = 'tt.agent.type.%s' % (vals['code'])
            self.sequence_prefix_id.name = 'Agent %s' % (vals['code'].title())
        if 'seq_prefix' in vals:
            self.sequence_prefix_id.prefix = '%s.%s' % (vals['seq_prefix'],self.sequence_prefix_id.prefix.split('.')[1])


    def create_menuitem(self):
        if not self.menuitem_id:
            ## create search view
            search_obj = self.env['ir.ui.view'].create({
                'name': 'tt.agent.view.search.inh.custom.%s' % (self.code),
                'model': 'tt.agent',
                'type': 'search',
                'inherit_id': self.env.ref('tt_base.tt_agent_view_search').id,
                'arch': '''
                <xpath expr="//group[@name='agent_type_filter']" position="inside">
                    <filter string="%s" name="%s" domain="[('agent_type_id','=',[%s,])]"/>
                </xpath>
                ''' % (self.name,self.code,self.id)
            })

            ## create action
            action_obj = self.env['ir.actions.act_window'].create({
                'name': 'Agent %s' % (self.name),
                'type': 'ir.actions.act_window',
                'res_model': 'tt.agent',
                'view_type': 'form',
                'view_mode': 'kanban,tree,form',

                'search_view_id': search_obj.id,
                'context': {
                    'form_view_ref': 'tt_base.tt_agent_form_view',
                    'kanban_view_ref': 'tt_base.tt_agent_kanban_view',
                    'search_default_%s' % (self.code) : 1,
                    'default_agent_type_id': self.id
                }
            })


        ## create custom menu item here
        menuitem_obj = self.env['ir.ui.menu'].create({
            'parent_id': self.env.ref('tt_base.menu_tour_travel_agent').id,
            'groups_id': [(4,self.env.ref('tt_base.group_tt_tour_travel_operator').id)],
            'name': self.name,
            'sequence': 35,
            'action': 'ir.actions.act_window,%s' % (action_obj.id)
        })
        self.menuitem_id = menuitem_obj.id

    def delete_menuitem(self):
        if self.menuitem_id:
            self.menuitem_id.action.search_view_id.unlink()
            self.menuitem_id.action.unlink()
            self.menuitem_id.unlink()

    # fixme : nanti akan diubah
    def calc_commission(self, amount, multiplier, carrier_id=False):
        rule_id = self.commission_rule_ids.filtered(lambda x: x.carrier_id.id == carrier_id or x.carrier_id.id == False)
        print(rule_id)
        if rule_id:
            rule_id = rule_id[0]
        else:
            return 0, 0, amount
        if rule_id.amount > 0:
            multiplier = rule_id.amount_multiplier == 'pppr' and multiplier or 1
            parent_commission = rule_id.amount * multiplier
            agent_commission = amount - parent_commission
            print('Amount : ' + str(amount))
            print('Parent Comm : ' + str(parent_commission))
            print('Agent Comm : ' + str(agent_commission))
        else:
            parent_commission = rule_id.parent_agent_amount * amount / 100
            agent_commission = rule_id.percentage * amount / 100
            print('Amount : ' + str(amount))
            print('Parent Comm : ' + str(parent_commission))
            print('Agent Comm : ' + str(agent_commission))

        ho_commission = amount - parent_commission - agent_commission
        print('HO Comm : ' + str(ho_commission))
        return agent_commission, parent_commission, ho_commission

    @api.multi
    def calc_recruitment_commission(self, agent_type_id, total_payment):
        comm_objs = self.recruitment_commission_ids.filtered(lambda x: x.rec_agent_type_id.id == agent_type_id.id)
        if comm_objs:
            return comm_objs[0].amount, comm_objs[0].parent_agent_amount, total_payment - comm_objs[0].amount - \
                   comm_objs[0].parent_agent_amount
        else:
            return 0, 0, total_payment

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'rounding_amount_type': self.rounding_amount_type,
            'rounding_places': self.rounding_places,
        }
        return res

    def toggle_non_updateable(self):
        templates_user = self.env['ir.model.data'].search([('module','=','tt_base'),
                                                     ('name','ilike','_template_user_')])
        value = not templates_user[0].noupdate
        for rec in templates_user:
            rec.noupdate = value

class TtAgentTypeBenefit(models.Model):
    _name = 'tt.agent.type.benefit'
    _description = 'Tour & Travel - Agent Type Benefit'

    title = fields.Text('Title', required=True)
    benefit = fields.Html('Benefit', required=True)


