from odoo import api, fields, models, _


class TtMasterTourOtherInfoMsg(models.Model):
    _name = 'tt.master.tour.otherinfo.messages'
    _description = 'Master Tour Other Info Messages'
    _order = 'sequence asc'

    name = fields.Text('Text', required=True, default='New')
    style = fields.Selection([('P','Plain'),('B','Bold'),('I','Italic'),('U','Underline')], 'Style', default='P')
    sequence = fields.Integer('Sequence', required=True, default=50)
    otherinfo_id = fields.Many2one('tt.master.tour.otherinfo', 'Other Info')


class TtMasterTourOtherInfo(models.Model):
    _name = 'tt.master.tour.otherinfo'
    _description = 'Master Tour Other Info'
    _order = 'sequence asc'

    name = fields.Text('Name', related='info_message_ids.name')
    info_message_ids = fields.One2many('tt.master.tour.otherinfo.messages', 'otherinfo_id', 'Messages')
    child_list_type = fields.Selection([('none', 'None'), ('number', 'Number (1, 2, 3)'), ('letter', 'Letter (a, b, c)'), ('dots', 'Dots (o, o, o)'), ('romans', 'Romans (I, II, III)')],'Child List Type', default='none')
    parent_id = fields.Many2one('tt.master.tour.otherinfo', 'Parent')
    child_ids = fields.One2many('tt.master.tour.otherinfo', 'parent_id', 'Children')
    master_tour_id = fields.Many2one('tt.master.tour', 'Master Tour')
    sequence = fields.Integer('Sequence', required=True, default=50)

    def convert_info_to_dict(self):
        msg_list = []
        for rec in self.info_message_ids:
            msg_list.append({
                'text': str(rec.name) + ' ',
                'style': rec.style,
                'sequence': rec.sequence
            })

        obj_child = []
        for rec in self.child_ids:
            obj_child.append(rec.convert_info_to_dict())

        return {
            'message': msg_list,
            'child_list_type': self.child_list_type,
            'sequence': self.sequence,
            'children': obj_child
        }


