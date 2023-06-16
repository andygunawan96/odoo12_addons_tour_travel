# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation Group Booking',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 56,
    'summary': 'Reservation Group Booking Module',
    'description': """
Tour & Travel - Reservation Group Booking
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
        'wizard/tt_set_pnr_wizard_view.xml',
        'security/ir.model.access.csv',
        'security/tt_reservation_groupbooking_security.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/ir_send_email.xml',
        'data/ir_cron_data.xml',
        'views/tt_reservation_groupbooking_menuheader.xml',
        'views/group_booking_views.xml',
        'views/tt_reservation_groupbooking_passenger_views.xml',
        'views/tt_provider_groupbooking_views.xml',
        'views/tt_reservation_groupbooking_service_charge_views.xml',
        'views/tt_ticket_groupbooking_views.xml',
        'views/tt_payment_rules_groupbooking_views.xml',
        'views/tt_tnc_groupbooking_views.xml',
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