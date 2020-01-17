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
        'views/tt_top_up_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
