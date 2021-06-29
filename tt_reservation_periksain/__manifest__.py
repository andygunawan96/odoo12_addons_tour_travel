# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_periksain',
    'version' : 'beta',
    'summary': 'Transport Reservation Periksain',
    'sequence': 60,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','tt_in_api_connector'],
    'data': [
        'views/menu_item_base.xml',

        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_periksain.xml',
        'data/tt_destination_periksain.xml',
        'data/tt_transport_carrier_periksain.xml',
        'data/ir_send_email.xml',
        'data/ir_cron_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/create_timeslot_wizard.xml',
        'wizard/confirm_order_wizard.xml',
        'wizard/force_issued_wizard_views.xml',
        'wizard/tt_split_reservation_wizard.xml',

        'views/tt_reservation_periksain_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_timeslot_periksain_views.xml',
        'views/tt_analyst_periksain_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_periksain_form_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
