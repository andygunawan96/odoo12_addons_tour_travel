# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Airline',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 52,
    'summary': 'Reservation Airline Module',
    'description': """
Tour & Travel - Reservation Airline
===================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base_setup','tt_base','tt_reservation','base_address_city','tt_in_api_connector'],
    'data': [
        'views/menu_item_base.xml',

        'wizard/tt_split_reservation_wizard.xml',
        'wizard/tt_get_booking_from_vendor.xml',

        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/res_config_settings_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_airline.xml',
        'data/tt_destination_airline.xml',
        'data/tt_transport_carrier_airline.xml',
        'data/tt_transport_carrier_type_airline.xml',
        'data/tt_transport_carrier_search_airline.xml',
        'data/tt_psg_limiter_rule_data.xml',
        'data/ir_send_email.xml',
        'data/tt_loyalty_program_data.xml',
        'data/tt_frequent_flyer_airline_data.xml',
        'data/tt_pnr_quota_price_list_airline_data.xml',
        'data/tt_pricing_agent_airline_data.xml',
        'data/tt_ssr_category_data.xml',
        'data/tt.ssr.list.csv',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',
        'wizard/tt_check_segment_wizard_views.xml',
        'wizard/tt_xls_pnr_matching_wizard_views.xml',

        'views/tt_reservation_airline.xml',
        'views/tt_provider_views.xml',
        'views/tt_journey_views.xml',
        'views/tt_segment_views.xml',
        'views/tt_leg_views.xml',
        'views/tt_banner_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_segment_addons_views.xml',
        'views/tt_fee_airline_views.xml',
        'views/tt_reservation_passenger_airline_form_views.xml',
        'views/tt_promo_code_airline_views.xml',
        'views/tt_frequent_flyer_airline_views.xml',
        'views/tt_ff_passenger_airline_views.xml',
        'views/tt_provider_airline_rule_views.xml',
        'views/tt_provider_airline_pricing_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
