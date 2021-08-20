# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_phc',
    'version' : 'beta',
    'summary': 'Transport Reservation phc',
    'sequence': 60,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','tt_in_api_connector','tt_report_common'],
    'data': [
        'views/menu_item_base.xml',

        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_phc.xml',
        'data/tt_destination_phc.xml',
        'data/tt_transport_carrier_phc.xml',
        'data/ir_send_email.xml',
        'data/ir_cron_data.xml',
        'data/tt_timeslot_phc_default_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/create_timeslot_wizard.xml',
        'wizard/confirm_order_wizard.xml',
        'wizard/force_issued_wizard_views.xml',
        'wizard/tt_split_reservation_wizard.xml',

        'views/tt_reservation_phc_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_timeslot_phc_views.xml',
        'views/tt_analyst_phc_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_phc_form_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
