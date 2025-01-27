# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Report Recap Reservation',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Agent Report Recap Reservation Module',
    'sequence': 20,
    'description': """
Tour & Travel - Agent Report Recap Reservation
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
        'views/tt_agent_report_recap_reservation_menuheader.xml',
        'wizard/tt_agent_report_recap_reservation_view.xml',
        'report/tt_agent_report_recap_reservation_menu.xml',
        'report/tt_agent_report_recap_reservation_template.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}