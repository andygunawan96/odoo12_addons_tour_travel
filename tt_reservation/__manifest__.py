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
        'security/ir_rule_data.xml',
        'data/ir_cron_data.xml',
        'views/tt_reservation_views.xml',
        'views/tt_reservation_psg_limiter.xml',
        'views/tt_ledger.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False
}