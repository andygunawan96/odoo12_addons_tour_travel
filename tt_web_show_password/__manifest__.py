# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Web Password Login',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 100,
    'summary': 'Hide and Show Password during Login',
    'description': """
Tour & Travel - Web Password Login
==========================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['web',],

    # always loaded
    'data': [
        'views/auth_signup_login.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}