# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - After Sales PHC',
    'version': '2.0',
    'category': 'Transaction',
    'sequence': 12,
    'summary': 'After Sales PHC Module',
    'description': """
Tour & Travel - After Sales PHC
===============================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base_setup', 'tt_reschedule', 'tt_reservation_phc'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'wizard/tt_reschedule_phc_wizard_views.xml',
        'wizard/set_real_amount_wizard_views.xml',
        'views/tt_reservation_phc.xml',
        'views/tt_reschedule_phc_line_views.xml',
        'views/tt_reschedule_phc_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
