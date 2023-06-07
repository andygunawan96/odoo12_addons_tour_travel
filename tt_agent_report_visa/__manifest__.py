# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Visa',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Visa Module',
    'sequence': 22,
    'description': """
Tour & Travel - Agent Report Visa
=================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_reservation_visa', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_visa_view.xml',
        'report/tt_agent_report_visa_report.xml',
        'report/tt_agent_report_visa_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}