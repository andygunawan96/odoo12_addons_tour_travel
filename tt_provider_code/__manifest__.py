# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Provider Code Data',
    'version': '2.0',
    'category': 'Data',
    'sequence': 63,
    'summary': 'Provider Code Data',
    'description': """
Tour & Travel - Provider Code Data
==================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_city_code'],

    # always loaded
    'data': [
        'data/tt.provider.code.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}