# -*- coding: utf-8 -*-
{
    'name': "tt_reservation_offline",
    'version': 'beta',
    'summary': 'Transport Reservation Offline',
    'sequence': 2,
    'description': """
        Module for Reservation Offline
    """,
    'category': 'booking',
    'author': "Rodextrip",
    'website': 'www.rodextrip.com',
    'images': [],
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
    # only loaded in demonstration mode
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}