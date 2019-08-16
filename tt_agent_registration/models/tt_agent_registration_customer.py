from odoo import models, fields, api, _
from ...tools import variables


class AgentRegistrationCustomer(models.Model):
    _inherit = 'tt.customer'

    agent_registration_id = fields.Many2one('tt.agent.registration', 'Agent Registration ID')


class AgentRegistrationCustomerContact(models.Model):
    _name = 'tt.agent.registration.customer'
    _description = 'Rodex Model'

    agent_registration_id = fields.Many2one('tt.agent.registration', 'Agent Registration ID')
    # agent_id = fields.Many2one('tt.agent', 'Agent')
    customer_id = fields.Many2one('tt.customer', 'Customer', readonly=True)
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')

    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status')
    religion = fields.Selection(variables.RELIGION, 'Religion')
    birth_date = fields.Date('Birth Date')
    email = fields.Char('Email')
    phone = fields.Char('Phone')  # akan diubah mjd One2many
    mobile = fields.Char('Mobile')  # akan diubah mjd One2many
