# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_sentramedika',
    'version' : 'beta',
    'summary': 'Transport Reservation Sentra Medika',
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
        'data/tt_provider_sentramedika.xml',
        'data/tt_destination_sentramedika.xml',
        'data/tt_transport_carrier_sentramedika.xml',
        'data/tt_timeslot_sentramedika_default_data.xml',
        'data/ir_send_email.xml',
        'data/ir_cron_data.xml',
        'data/report_common_setting_data_sentramedika.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/create_timeslot_wizard.xml',
        'wizard/confirm_order_wizard.xml',
        'wizard/cancel_order_wizard.xml',
        'wizard/force_issued_wizard_views.xml',
        'wizard/tt_split_reservation_wizard.xml',

        'views/tt_reservation_sentramedika_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_price_list_sentramedika_views.xml',
        'views/tt_timeslot_sentramedika_views.xml',
        'views/tt_analyst_sentramedika_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_sentramedika_form_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}