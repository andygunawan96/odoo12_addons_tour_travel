# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector Reconcile',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector Reconcile Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector Reconcile
===================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reservation'],

    # always loaded
    'data': [
        'data/ir_cron_data.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}