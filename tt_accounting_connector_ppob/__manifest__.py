# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector PPOB',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector PPOB Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector PPOB
===================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reservation_ppob'],

    # always loaded
    'data': [
        'views/tt_reservation_setup_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}