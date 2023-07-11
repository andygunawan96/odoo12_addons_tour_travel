# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Module',
    'sequence': 14,
    'description': """
Tour & Travel - Agent Report
============================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_reservation', 'tt_agent_sales', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_common_view.xml',
        'wizard/tt_agent_report_ledger_view.xml',
        'wizard/tt_agent_report_excel_output_wizard.xml',
        'report/tt_agent_report_ledger_menu.xml',
        'report/tt_agent_report_ledger_template.xml'
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}