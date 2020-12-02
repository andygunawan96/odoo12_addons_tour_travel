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
    'depends': ['base_setup', 'tt_base', 'tt_accounting', 'tt_reservation', 'tt_reservation_airline', 'tt_agent_sales'],
    'data': [
        'data/ir_sequence_data.xml',
        'wizard/tt_reschedule_wizard_views.xml',
        'wizard/set_real_amount_wizard_views.xml',
        'wizard/set_new_segment_pnr_wizard_views.xml',
        'views/tt_segment_addons_views.xml',
        'views/tt_segment_views.xml',
        'views/tt_reschedule_views.xml',
        'views/tt_leg_views.xml',
        'views/tt_reservation_airline.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
