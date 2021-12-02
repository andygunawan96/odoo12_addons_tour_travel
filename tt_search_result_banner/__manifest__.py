# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Search Result Banner',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 6,
    'summary': 'Search Result Banner Module',
    'description': """
Tour & Travel - Search Result Banner
===============================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base'],

    # always loaded
    'data': [
        'data/master_cabin_class.xml',
        'security/ir.model.access.csv',
        'views/tt_search_result_banner_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}