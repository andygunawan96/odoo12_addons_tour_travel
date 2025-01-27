# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector Activity',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector Activity Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector Activity
===================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reservation_activity'],

    # always loaded
    'data': [
        'data/ir_cron_data.xml',
        'views/tt_reservation_setup_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}