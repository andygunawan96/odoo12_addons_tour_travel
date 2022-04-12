# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Connector PHC',
    'version': '2.0',
    'category': 'Connector',
    'summary': 'Accounting Connector PHC Module',
    'sequence': 100,
    'description': """
Tour & Travel - Accounting Connector PHC
===================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_accounting_connector', 'tt_reservation_phc'],

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