# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector Reschedule Periksain',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector Reschedule Periksain Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector Reschedule Periksain
=========================================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reschedule_periksain'],

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