# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Payment',
    'version': '2.0',
    'category': 'Transaction',
    'sequence': 12,
    'summary': 'Payment Module',
    'description': """
Tour & Travel - Payment
=======================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base_setup', 'tt_base', 'tt_accounting'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'views/tt_payment_views.xml',
        'views/tt_top_up_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
