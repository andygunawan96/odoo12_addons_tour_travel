# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Tour',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Tour Module',
    'sequence': 29,
    'description': """
Tour & Travel - Agent Sales Tour
================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_tour'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_tour.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}