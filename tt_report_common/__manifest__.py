# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Report Common',
    'version': '2.0',
    'category': 'Report',
    'sequence': 80,
    'summary': 'Report Core Module',
    'description': """
Tour & Travel - Report Common
=============================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['tt_base'],

    # always loaded
    'data': [
        'data/e_paperformat.xml',
        'data/report_data.xml',
        'data/report_common_setting_data.xml',
        'report/printout_ticket_airline_template.xml',
        'report/printout_ticket_train_template.xml',
        'report/printout_ticket_event_template.xml',
        'report/printout_ticket_periksain_template.xml',
        'report/printout_ticket_medical_template.xml',
        'report/printout_ticket_bus_template.xml',
        'report/printout_ticket_insurance_template.xml',
        'report/printout_invoice_template.xml',
        'report/printout_ho_invoice_template.xml',
        'report/printout_vendor_invoice_template.xml',
        'report/printout_billing_template.xml',
        'report/printout_itinerary_template.xml',
        'report/printout_topup_template.xml',
        'report/printout_hotel_voucher_template.xml',
        'report/printout_ppob_bills_template.xml',
        'report/printout_refund_template.xml',
        'report/printout_reschedule_template.xml',
        'report/printout_expenses_invoice_template.xml',
        'report/printout_voucher_template.xml',
        'report/printout_letter_guarantee_template.xml',
        'security/ir.model.access.csv',
        'views/tt_report_setting_views.xml',
        'views/menu_item_base.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}