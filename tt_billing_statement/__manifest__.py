# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_billing_statement',
    'version' : 'beta',
    'summary': 'billing statement',
    'sequence': 2,
    'description': """
Billing Statement
""",
    'category': 'billing',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_accounting', 'tt_agent_sales', 'tt_payment'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_billing_cycle.xml',
        'security/ir.model.access.csv',

        'views/tt_agent_invoice_views.xml',
        'views/tt_billing_statement_views.xml',
        'views/tt_customer_parent_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
