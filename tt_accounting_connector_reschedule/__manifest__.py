# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector Reschedule',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector Reschedule Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector Reschedule
===============================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reschedule'],

    # always loaded
    'data': [
        'data/ir_cron_data.xml',
        'views/tt_reservation_setup_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}