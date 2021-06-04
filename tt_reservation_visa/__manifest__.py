# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Visa',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 61,
    'summary': 'Reservation Visa Module',
    'description': """
Tour & Travel - Reservation Visa
================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_engine_pricing', 'tt_traveldoc', 'tt_reservation', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_visa.xml',
        'data/tt_reservation_visa_pricelist.xml',
        'data/tt_master_visa_locations.xml',
        'data/tt.master.visa.handling.csv',
        'data/tt_api_webhook_data.xml',
        'data/tt_pricing_agent_visa_data.xml',

        'views/tt_reservation_visa_menuheader.xml',
        'views/tt_reservation_visa_views.xml',
        'views/tt_reservation_visa_order_passengers_views.xml',
        'views/tt_master_visa_locations_views.xml',
        'views/tt_master_visa_handling_views.xml',
        'views/tt_reservation_visa_pricelist_views.xml',
        'views/tt_provider_visa_views.xml',
        'views/tt_reservation_visa_service_charge_views.xml',
        'views/tt_reservation_visa_vendor_views.xml',
        'views/tt_visa_sync_product_wizard.xml',
        'views/tt_visa_sync_to_children_wizard.xml',
        'report/printout_menu.xml',
        'report/printout_visa_ho_template.xml',
        'report/printout_visa_customer_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}