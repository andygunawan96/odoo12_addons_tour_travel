# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Agent Registration',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Agent Registration Module',
    'sequence': 22,
    'description': """
Tour & Travel - Agent Sales Agent Registration
==============================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'tt_agent_sales', 'tt_agent_registration'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}