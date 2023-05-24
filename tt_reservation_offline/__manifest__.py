# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Offline',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 56,
    'summary': 'Reservation Offline Module',
    'description': """
Tour & Travel - Reservation Offline
===================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_engine_pricing', 'tt_reservation', 'tt_report_common'],

    # always loaded
    'data': [
        'wizard/tt_split_reservation_wizard.xml',
        'security/ir.model.access.csv',
        'security/tt_reservation_offline_security.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_other.xml',
        'data/ir_send_email.xml',
        'views/tt_reservation_offline_menuheader.xml',
        'views/issued_offline_views.xml',
        'views/tt_reservation_offline_lines_views.xml',
        'views/tt_reservation_offline_passenger_views.xml',
        'views/tt_provider_offline_views.xml',
        'views/tt_reservation_offline_service_charge_views.xml',
        'report/paperformat_A4.xml',
        'report/printout_menu.xml',
        'report/printout_invoice_template.xml',
        'report/printout_invoice_ticket_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}