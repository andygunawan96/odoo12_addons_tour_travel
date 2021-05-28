# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Offline',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Offline Module',
    'sequence': 18,
    'description': """
Tour & Travel - Agent Report Offline
====================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'tt_base', 'tt_agent_report', 'tt_reservation_offline'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_offline_view.xml',
        'report/tt_agent_report_offline_menu.xml',
        'report/tt_agent_report_offline_template.xml',
        'report/tt_agent_report_offline_template_HO.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}