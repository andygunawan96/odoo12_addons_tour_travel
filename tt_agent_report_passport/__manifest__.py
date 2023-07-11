# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Passport',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Passport Module',
    'sequence': 19,
    'description': """
Tour & Travel - Agent Report Passport
=====================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_reservation_passport', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_passport_view.xml',
        'report/tt_agent_report_passport_report.xml',
        'report/tt_agent_report_passport_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}