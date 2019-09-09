# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'tt_reservation_hotel',
    'version': 'beta',
    'summary': 'reservation hotel',
    'sequence': 2,
    'description': """
TT_RESERVATION_HOTEL
""",
    'category': 'booking',
    'website': '',
    'images': [],
    'depends': ['base_setup','tt_base','tt_reservation','base_address_city', 'tt_merge_record'],
    'data': [
        'data/provider_type_data.xml',
        'data/ir_sequence_data.xml',
        'data/hotel_type_data.xml',
        'data/tt.hotel.facility.type.csv',
        'data/res.city.type.csv',
        'data/res.country.state.csv',
        'data/res.city.csv',
        # 'data/res.country.district.csv',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        # 'views/charge_rule_views.xml',
        'views/facility_type_views.xml',
        'views/facility_views.xml',
        'views/hotel_information_views.xml',
        'views/hotel_type_views.xml',
        'views/landmark_views.xml',
        'views/meal_type_views.xml',
        # 'views/room_booking_views.xml',
        'views/room_information_views.xml',
        'views/room_type_views.xml',
        'views/city_views.xml',
        'views/tt_reservation_hotel_views.xml',
        'views/provider_data_sync_views.xml',
        'views/menu_item_base.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
