# -*- coding: utf-8 -*-
{
    'name': "tt_accounting",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Skytors",
    'website': "http://www.skytors.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Transaction',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'tt_base', 'tt_in_api_connector'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/admin_fee_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',
        'views/tt_master_admin_fee_views.xml',
        'views/tt_ledger_views.xml',
        'views/tt_adjustment_views.xml',
        'wizard/tt_adjustment_wizard_view.xml',
        'views/tt_refund_views.xml',
        'wizard/tt_refund_wizard_view.xml',
        'views/tt_agent_views.xml',
        'views/tt_top_up_views.xml',
        'views/tt_customer_parent_views.xml',
        'views/tt_pnr_quota_views.xml',

        'views/ir_ui_menu_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
