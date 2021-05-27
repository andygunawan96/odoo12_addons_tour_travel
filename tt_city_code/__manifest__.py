# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - City Code Data',
    'version': '2.0',
    'category': 'Data',
    'sequence': 100,
    'summary': 'City Code Data',
    'description': """
Tour & Travel - City Code Data
==============================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': [],

    # always loaded
    'data': [
        'data/res.country.state.csv',
        'data/res.city.csv',
        'data/tt.destination.alias.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}