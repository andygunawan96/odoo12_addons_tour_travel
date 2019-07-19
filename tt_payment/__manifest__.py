# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tour Travel Payment',
    'version' : 'beta',
    'summary': 'Payment',
    'sequence': 2,
    'description': """
TT_PAYMENT
""",
    'category': 'billing',
    'website': '',
    'images': [],
    'depends': ['base_setup', 'tt_base', 'tt_accounting'],
    'data': [
        'data/ir_sequence_data.xml',
        'views/tt_payment_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
