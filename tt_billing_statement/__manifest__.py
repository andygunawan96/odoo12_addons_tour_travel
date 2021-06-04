# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Billing Statement',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Billing Statement Module',
    'sequence': 40,
    'description': """
Tour & Travel - Billing Statement
=================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends' : ['base_setup','tt_base','tt_accounting', 'tt_agent_sales', 'tt_payment'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_billing_cycle.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',

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
    'application': False,
    'auto_install': False,
}
