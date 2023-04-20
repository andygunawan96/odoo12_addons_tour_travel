# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Agent Monthly Fee',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 62,
    'summary': 'Agent Monthly Fee Module',
    'description': """
Tour & Travel - Agent Monthly Fee
=================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_base', 'tt_accounting'],
    'data': [
        # 'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'views/tt_monthly_fee_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
