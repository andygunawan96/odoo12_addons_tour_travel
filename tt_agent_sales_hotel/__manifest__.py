# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Hotel',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Hotel Module',
    'sequence': 25,
    'description': """
Tour & Travel - Agent Sales Hotel
=================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': [
        'tt_agent_sales',
        'tt_reservation_hotel'
    ],

    'data': [
        'views/tt_reservation_hotel.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}