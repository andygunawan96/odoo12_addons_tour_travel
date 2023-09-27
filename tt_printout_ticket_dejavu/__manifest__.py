# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Printout Ticket Dejavu',
    'version': '2.0',
    'category': 'Report',
    'sequence': 80,
    'summary': 'Change Template #1 to Dejavu Font Family',
    'description': """
Tour & Travel - Printout Ticket Dejavu
======================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['tt_report_common'],

    # always loaded
    'data': [
        'report/printout_ticket_airline_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}