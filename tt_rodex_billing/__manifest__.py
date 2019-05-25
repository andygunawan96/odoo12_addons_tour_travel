# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_billing_statement',
    'version' : 'beta',
    'summary': 'billing statement',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'billing',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_accounting', 'tt_agent_sales'],
    'data': [
        'data/ir_sequence_data.xml',
        # 'security/ir.model.access.csv',
        'views/tt_agent_invoice_views.xml',
        'views/tt_billing_statement_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
