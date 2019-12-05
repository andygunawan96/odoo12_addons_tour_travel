# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tour Travel Reschedule',
    'version' : 'beta',
    'summary': 'Reschedule',
    'sequence': 2,
    'description': """
TT_RESCHEDULE
""",
    'category': 'tour_travel',
    'website': '',
    'images': [],
    'depends': ['base_setup', 'tt_base', 'tt_accounting', 'tt_reservation', 'tt_reservation_airline'],
    'data': [
        'data/ir_sequence_data.xml',
        'wizard/tt_reschedule_wizard_views.xml',
        'views/tt_reschedule_views.xml',
        'views/tt_reservation_airline.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
