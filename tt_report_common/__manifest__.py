# -*- coding: utf-8 -*-
{
    'name': "tt_report_common",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "PT. Roda Express Travel and Tours",
    'website': "http://www.skytors.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Report Common',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['tt_base'],

    # always loaded
    'data': [
        'data/e_paperformat.xml',
        'data/report_data.xml',
        'report/printout_ticket_airline_template.xml',
        'report/printout_ticket_train_template.xml',
        'report/printout_invoice_template.xml',
        'report/printout_ho_invoice_template.xml',
        'report/printout_billing_template.xml',
        'report/printout_itinerary_template.xml',
        'report/printout_topup_template.xml',
        'report/printout_hotel_voucher_template.xml',
        'report/printout_refund_template.xml',
        'report/printout_reschedule_template.xml',
        'report/printout_expenses_invoice_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}