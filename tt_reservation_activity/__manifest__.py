# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_activity',
    'version' : 'beta',
    'summary': 'transport dummy activity',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_agent_sales'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_activity.xml',
        'security/ir.model.access.csv',
        # 'security/ir_rule_data.xml',
        # 'report/printout_invoice_templates.xml',
        'views/menu_item_base.xml',
        'views/tt_activity_voucher_wizard.xml',
        'views/tt_activity_sync_product_wizard.xml',
        'views/tt_activity_category_views.xml',
        'views/tt_reservation_activity_option_views.xml',
        'views/tt_master_activity_views.xml',
        'views/tt_reservation_activity_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_service_charge_views.xml'
        # 'views/tt_activity_printout_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
