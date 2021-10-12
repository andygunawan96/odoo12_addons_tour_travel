# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_labpintar',
    'version' : 'beta',
    'summary': 'Transport Reservation Lab Pintar',
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
        'data/tt_provider_labpintar.xml',
        'data/tt_destination_labpintar.xml',
        'data/tt_transport_carrier_labpintar.xml',
        'data/tt_timeslot_labpintar_default_data.xml',
        'data/ir_send_email.xml',
        'data/ir_cron_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/create_timeslot_wizard.xml',
        'wizard/confirm_order_wizard.xml',
        'wizard/cancel_order_wizard.xml',
        'wizard/force_issued_wizard_views.xml',
        'wizard/tt_split_reservation_wizard.xml',

        'views/tt_reservation_labpintar_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_price_list_labpintar_views.xml',
        'views/tt_timeslot_labpintar_views.xml',
        'views/tt_analyst_labpintar_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_labpintar_form_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
