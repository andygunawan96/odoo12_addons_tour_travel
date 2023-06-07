# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Reservation',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 50,
    'summary': 'Reservation Core Module',
    'description': """
Tour & Travel - Reservation
===========================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_api_management', 'tt_in_api_connector', 'tt_vouchers', 'tt_engine_pricing', 'tt_engine_pricing_v2', 'tt_reservation_request'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_cron_data.xml',

        'wizard/tt_reconcile_manual_match_wizard_view.xml',

        'views/tt_reservation_views.xml',
        'views/tt_reservation_psg_limiter.xml',
        'views/tt_refund_views.xml',
        'views/tt_ledger.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_views.xml',
        'views/tt_reconcile_transaction_views.xml',

        'wizard/tt_reconcile_transaction_wizard_view.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}