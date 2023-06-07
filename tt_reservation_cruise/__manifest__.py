# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Cruise',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 53,
    'summary': 'Reservation Cruise Module',
    'description': """
Tour & Travel - Reservation Cruise
==================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_reservation', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/tt_provider_type_data.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}