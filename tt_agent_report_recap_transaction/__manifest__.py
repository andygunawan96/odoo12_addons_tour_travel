# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Recap Transaction Module',
    'sequence': 21,
    'description': """
Tour & Travel - Agent Report Recap Transaction
==============================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_recap_transaction_view.xml',
        'wizard/tt_agent_report_recap_aftersales_view.xml',
        'report/tt_agent_report_recap_transaction_menu.xml',
        'report/tt_agent_report_recap_transaction_template.xml',
        'report/tt_agent_report_recap_aftersales_menu.xml',
        'report/tt_agent_report_recap_aftersales_template.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}