# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Billing',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Billing Module',
    'sequence': 16,
    'description': """
Tour & Travel - Agent Report Billing
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
        'wizard/tt_agent_report_billing_view.xml',
        'report/tt_agent_report_billing_menu.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}