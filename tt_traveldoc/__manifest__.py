# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Travel Doc',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 100,
    'summary': 'Travel Doc Module',
    'description': """
Tour & Travel - Travel Doc
==========================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        # 'data/tt.traveldoc.type.csv',
        'views/tt_traveldoc_type_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}