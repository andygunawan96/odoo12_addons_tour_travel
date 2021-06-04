# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Report Airline',
    'version': '2.0',
    'category': 'Report',
    'sequence': 84,
    'summary': 'Airline Reservation Report Module',
    'description': """
Tour & Travel - Reservation Report Airline
==========================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_agent_report', 'tt_reservation_airline'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_reservation_report_airline_view.xml',
        'report/tt_reservation_report_airline_menu.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}