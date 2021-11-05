# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Insurance',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Insurance Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales Insurance
=====================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_insurance'],

    # always loaded
    'data': [
        'views/tt_reservation_insurance.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}