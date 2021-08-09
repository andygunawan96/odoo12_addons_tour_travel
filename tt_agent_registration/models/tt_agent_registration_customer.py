from odoo import models, fields, api, _
from ...tools import variables

LEVEL = [
    ('operator', 'Operator'),
    ('supervisor', 'Supervisor'),
    ('manager', 'Manager')
]


class AgentRegistrationCustomerContact(models.Model):
    _name = 'tt.agent.registration.customer'
    _description = 'Agent Registration Customer'

    agent_registration_id = fields.Many2one('tt.agent.registration', 'Agent Registration ID')
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')

    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status')
    religion = fields.Selection(variables.RELIGION, 'Religion')
    birth_date = fields.Date('Birth Date')
    email = fields.Char('Email', required=True)
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')

    job_position = fields.Char('Job Position')
    user_level = fields.Selection(LEVEL, 'User Level', default='manager')
