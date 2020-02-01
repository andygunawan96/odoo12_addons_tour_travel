# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_airline',
    'version' : 'beta',
    'summary': 'transport dummy airline',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_in_api_connector'],
    'data': [
        'views/menu_item_base.xml',

        'wizard/tt_split_reservation_wizard.xml',
        'wizard/tt_get_booking_from_vendor.xml',

        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_airline.xml',
        'data/tt_destination_airline.xml',
        'data/tt_transport_carrier_airline.xml',
        'data/tt_transport_carrier_search_airline.xml',
        'data/tt_psg_limiter_rule_data.xml',
        # 'data/tt_cabin_class.xml',
        # 'data/tt_product_class.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',

        'views/tt_reservation_airline.xml',
        'views/tt_provider_views.xml',
        'views/tt_journey_views.xml',
        'views/tt_segment_views.xml',
        'views/tt_leg_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_segment_addons_views.xml',
        'views/tt_fee_airline.xml',
        'views/tt_reservation_passenger_airline_form_views.xml',
        'views/tt_promo_code_airline_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
