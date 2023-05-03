# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tour & Travel - Accounting Connector',
    'version' : '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector',
    'sequence': 99,
    'description': """
Tour & Travel - Accounting Connector
====================================
Key Features
------------
""",
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends' : ['tt_base', 'tt_accounting', 'tt_accounting_setup', 'tt_in_api_connector'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_cron_data.xml',
        'views/tt_agent_views.xml',
        'views/ledger_views.xml',
        'views/tt_payment_acquirer_views.xml',
        'views/accounting_queue_views.xml',
        'wizard/generate_csv_wizard_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
