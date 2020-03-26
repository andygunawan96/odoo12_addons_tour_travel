# -*- coding: utf-8 -*-
{
    'name': "tt_reservation_passport",
    'version' : 'beta',
    'summary': """Passport Document""",
    'sequence': 2,
    'description': """
        TT RESERVATION PASSPORT
    """,
    'category': 'booking',
    'author': "IT Rodex",
    'website': "http://www.rodextrip.com",
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_engine_pricing', 'tt_traveldoc', 'tt_reservation', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
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
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}