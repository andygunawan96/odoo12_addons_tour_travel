# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Balance',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Balance Module',
    'sequence': 15,
    'description': """
Tour & Travel - Agent Report Balance
====================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_report_common', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/tt_agent_report_balance_log.xml',
        'wizard/tt_agent_report_balance_view.xml',
        'report/tt_agent_report_balance_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
