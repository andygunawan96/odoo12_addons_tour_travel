# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector Periksain',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector Periksain Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector Periksain
==============================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reservation_periksain'],

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