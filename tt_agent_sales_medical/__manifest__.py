# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales PHC',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales PHC Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales PHC
=================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_medical'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_medical.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}