# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - After Sales Periksain',
    'version': '2.0',
    'category': 'Transaction',
    'sequence': 12,
    'summary': 'After Sales Periksain Module',
    'description': """
Tour & Travel - After Sales Periksain
=====================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base_setup', 'tt_reschedule', 'tt_reservation_periksain'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'wizard/tt_reschedule_periksain_wizard_views.xml',
        'wizard/set_real_amount_wizard_views.xml',
        'views/tt_reservation_periksain.xml',
        'views/tt_reschedule_periksain_line_views.xml',
        'views/tt_reschedule_periksain_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
