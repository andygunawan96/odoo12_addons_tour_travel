# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Google State and City Code 2',
    'version': '2.0',
    'category': 'Data',
    'sequence': 100,
    'summary': 'Google State and City Code Data',
    'description': """
Tour & Travel - Google State and City Code 2
============================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': [
        'base_address_city', 'tt_city_google',
    ],

    # always loaded
    'data': [
        'data/res.city.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}