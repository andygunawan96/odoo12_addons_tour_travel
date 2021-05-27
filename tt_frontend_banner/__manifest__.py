# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Frontend Banner',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 6,
    'summary': 'Frontend Banner Module',
    'description': """
Tour & Travel - Frontend Banner
===============================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base'],

    # always loaded
    'data': [
        'data/tt_frontend_banner_data.xml',
        'security/ir.model.access.csv',
        'views/tt_frontend_banner_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}