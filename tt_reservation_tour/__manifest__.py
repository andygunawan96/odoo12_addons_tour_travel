# -*- coding: utf-8 -*-
{
    'name' : 'tt_reservation_tour',
    'version' : 'beta',
    'summary': 'Transport Reservation Tour',
    'sequence': 2,

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'booking',
    'version': '0.1',

    # any module necessary for this one to work correctly
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
    'application': True,
    'auto_install': False,
}
