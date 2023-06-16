# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Passport',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 57,
    'summary': 'Reservation Passport Module',
    'description': """
Tour & Travel - Reservation Passport
====================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_engine_pricing', 'tt_traveldoc', 'tt_reservation', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        # 'data/ir_send_email.xml',
        'data/tt_provider_type_data.xml',
        'data/tt.reservation.passport.pricelist.csv',
        'data/tt_provider_passport.xml',
        'views/tt_reservation_passport_menuheader.xml',
        'views/tt_reservation_passport_views.xml',
        'views/tt_reservation_passport_order_passengers_views.xml',
        'views/tt_reservation_passport_service_charge_views.xml',
        'views/tt_reservation_passport_pricelist_views.xml',
        'views/tt_passport_sync_product_wizard.xml',
        'views/tt_reservation_passport_vendor_views.xml',
        'views/tt_provider_passport_views.xml',
        'report/printout_menu.xml',
        'report/printout_passport_customer_template.xml',
        'report/printout_passport_ho_template.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}