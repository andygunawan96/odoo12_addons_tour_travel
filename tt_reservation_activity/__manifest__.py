# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Activity',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 51,
    'summary': 'Reservation Activity Module',
    'description': """
Tour & Travel - Reservation Activity
====================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base_setup','tt_base','tt_reservation','base_address_city'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_activity.xml',
        'data/tt_transport_carrier_activity.xml',
        'data/tt_api_webhook_data.xml',
        'data/ir_send_email.xml',
        'data/tt_pricing_agent_activity_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'wizard/force_issued_wizard_views.xml',
        'views/menu_item_base.xml',
        'views/tt_activity_voucher_wizard.xml',
        'views/tt_activity_sync_product_wizard.xml',
        'views/tt_activity_sync_to_children_wizard.xml',
        'views/tt_activity_category_views.xml',
        'views/tt_reservation_activity_option_views.xml',
        'views/tt_master_activity_views.xml',
        'views/tt_reservation_activity_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_activity_form_views.xml',
        'views/tt_reservation_activity_details_views.xml'
        # 'views/tt_activity_printout_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
