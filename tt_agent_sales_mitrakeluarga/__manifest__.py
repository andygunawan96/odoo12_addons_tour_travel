# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Mitra Keluarga',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Mitra Keluarga Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales Mitra Keluarga
=================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_mitrakeluarga'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_mitrakeluarga.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}