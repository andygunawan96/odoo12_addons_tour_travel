from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_ticket = fields.Boolean('Is Ticket?', default=False)
    ticket_usage = fields.Selection([
        ('hotel', 'For Hotel'),
    ], 'Usage')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    voucher_type = fields.Selection([
        ('all', 'All'),
        ('many', 'Selected'),
        # ('one', 'One Room'),
    ], 'Used Type')
    room_ids = fields.Many2many('tt.room.info', 'ticket_room_rel', 'ticket_id', 'room_id', 'Room(s)')
    tac = fields.Text('Term and Condition')

    @api.depends('hotel_id')
    @api.onchange('hotel_id')
    def change_domain_room_ids(self):
        for product in self:
            domain = {'room_ids': []}
            if product.hotel_id:
                product.room_info_ids = False
                domain = {'room_ids': [('id', 'in', product.hotel_id.room_info_ids.ids)]}
            return {'domain': domain}


class Product(models.Model):
    _inherit = 'product.product'

    is_ticket = fields.Boolean('Is Ticket?', related='product_tmpl_id.is_ticket')


class SaleOrderVoucher(models.Model):
    _name = 'sale.order.voucher'
    _inherit = 'sale.order'

    order_line = fields.One2many('sale.order.line.voucher', 'order_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)


class SaleOrderLineVoucher(models.Model):
    _name = 'sale.order.line.voucher'
    _inherit = 'sale.order.line'

    order_id = fields.Many2one('sale.order.voucher', string='Order Reference', required=True, ondelete='cascade', index=True,
                               copy=False)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True), ('is_ticket', '=', True)],
                                 change_default=True, ondelete='restrict', required=True)


class PurchaseOrderVoucher(models.Model):
    _name = 'purchase.order.voucher'
    _inherit = 'purchase.order'

    order_line = fields.One2many('purchase.order.line.voucher', 'order_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)


class PurchaseOrderLineVoucher(models.Model):
    _name = 'purchase.order.line.voucher'
    _inherit = 'purchase.order.line'

    order_id = fields.Many2one('purchase.order.voucher', string='Order Reference', index=True, required=True,
                               ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True),('is_ticket','=',True)],
                                 change_default=True, required=True)

    qty_available = fields.Float('Quantity On Hand', compute='_compute_quantities',
                                 digits=dp.get_precision('Product Unit of Measure'))
