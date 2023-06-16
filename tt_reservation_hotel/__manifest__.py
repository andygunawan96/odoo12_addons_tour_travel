# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Hotel',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 55,
    'summary': 'Reservation Hotel Module',
    'description': """
Tour & Travel - Reservation Hotel
=================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base_setup','tt_base','tt_reservation','base_address_city', 'tt_merge_record'],
    'data': [
        'data/ir_cron_data.xml',
        'data/provider_type_data.xml',
        'data/ir_sequence_data.xml',
        'data/hotel_type_data.xml',
        'data/tt.hotel.facility.type.csv',
        'data/res.city.type.csv',
        # 'data/res.country.state.csv',
        'data/res.city.csv',
        'data/ir_send_email.xml',
        'data/tt_transport_carrier_hotel.xml',
        'data/tt_api_webhook_data.xml',
	    'data/tt_pnr_quota_price_list_hotel_data.xml',
        'data/tt_pricing_agent_hotel_data.xml',

        # 'data/tt.provider.code.csv',
        # 'data/res.country.district.csv',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',

        # 'views/charge_rule_views.xml',
        'views/hotel_information_views.xml',
        'views/hotel_type_views.xml',
        'views/facility_type_views.xml',
        'views/facility_views.xml',
        'views/landmark_views.xml',
        'views/meal_type_views.xml',
        # 'views/room_booking_views.xml',
        'views/room_information_views.xml',
        'views/room_type_views.xml',
        'views/city_views.xml',
        'views/hotel_compare_views.xml',
        'views/tt_reservation_hotel_views.xml',
        'views/tt_provider_views.xml',
        'views/provider_data_sync_views.xml',
        'views/hotel_destination_views.xml',
        'views/menu_item_base.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
