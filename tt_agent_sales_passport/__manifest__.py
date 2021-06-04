# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Passport',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Passport Module',
    'sequence': 27,
    'description': """
Tour & Travel - Agent Sales Passport
====================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_passport'],

    # always loaded
    'data': [
        'views/tt_reservation_passport.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}