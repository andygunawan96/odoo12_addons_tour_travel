# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Tour',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 59,
    'summary': 'Reservation Tour Module',
    'description': """
Tour & Travel - Reservation Tour
================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'mail', 'tt_reservation', 'survey', 'tt_base'],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_tour.xml',
        'data/tt_transport_carrier_tour.xml',
        'data/ir_config_parameter.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',
        'data/tt_pricing_agent_tour_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'wizard/force_issued_wizard_views.xml',
        'wizard/tour_assign_products_wizard_views.xml',
        'views/menu_item_base.xml',
        'views/tt_tour_sync_product_wizard.xml',
        'views/tt_tour_sync_to_children_wizard.xml',
        'views/tt_reservation_tour_views.xml',
        'views/tt_master_tour_views.xml',
        'views/tt_master_tour_lines_views.xml',
        'views/tt_master_tour_special_dates_views.xml',
        'views/tt_master_tour_pricing_views.xml',
        'views/tt_master_tour_other_charges_views.xml',
        'views/tt_master_tour_quotation_views.xml',
        'views/tt_tour_master_locations_views.xml',
        'views/tt_master_tour_provider_views.xml',
        'views/tt_master_tour_otherinfo_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_tour_form_views.xml',
        'views/tt_request_tour_views.xml',
        'wizard/import_request_tour_wizard_views.xml',
        'views/ir_ui_menu_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
