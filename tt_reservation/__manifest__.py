# -*- coding: utf-8 -*-
{
    'name': 'tt_reservation',
    'version': '1.1',
    'category': 'Tour & Travel',
    'sequence': 1,
    'summary': 'Tour & Travel - Base',
    'description': """
        Tour & Travel - Reservation
        ====================
        Key Features
        ------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_accounting'],
    'data': [
        'security/ir.model.access.csv',

        'views/tt_reservation_views.xml',
        'views/tt_ledger.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False
}