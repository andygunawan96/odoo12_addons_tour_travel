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
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'tt_base', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_recap_transaction_view.xml',
        'report/tt_agent_report_recap_transaction_menu.xml',
        'report/tt_agent_report_recap_transaction_template.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}