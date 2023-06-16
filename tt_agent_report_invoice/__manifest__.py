# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Invoice',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Invoice Module',
    'sequence': 17,
    'description': """
Tour & Travel - Agent Report Invoice
====================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_invoice_view.xml',
        'report/tt_agent_report_invoice_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}