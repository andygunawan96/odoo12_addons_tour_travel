# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Agent Monthly Fee',
    'version': 'beta',
    'summary': 'Monthly Fee',
    'sequence': 10,
    'description': """
TT_PAYMENT
""",
    'category': 'monthly fee',
    'website': '',
    'images': [],
    'depends': ['tt_base', 'tt_accounting'],
    'data': [
        # 'data/ir_sequence_data.xml',
        'views/tt_monthly_fee_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
