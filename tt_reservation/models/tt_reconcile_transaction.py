from odoo import api,fields,models
from datetime import datetime
from odoo.exceptions import UserError
from io import BytesIO
import xlsxwriter
import base64
import pytz
import logging,traceback
from ...tools import variables, util, ERR
from ...tools import tools_excel

_logger = logging.getLogger()


class TtRefundInherit(models.Model):
    _inherit = 'tt.refund'

    reconcile_state = fields.Selection(variables.RESV_RECONCILE_STATE, 'Reconcile State', default='not_reconciled',
                                       compute='_compute_reconcile_state', store=True)
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines', 'Reconciled', readonly=True)
    reconcile_time = fields.Datetime('Reconcile Time', readonly=True)

    @api.depends('reconcile_line_id')
    def _compute_reconcile_state(self):
        for rec in self:
            if rec.reconcile_line_id and rec.reconcile_line_id.state == 'match':
                rec.reconcile_state = 'reconciled'
            elif rec.reconcile_line_id and rec.reconcile_line_id.state == 'cancel':
                rec.reconcile_state = 'cancel'
            else:
                rec.reconcile_state = 'not_reconciled'


class TtReconcileTransaction(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reconcile.transaction'
    _description = 'Reconcile'
    _rec_name = 'display_reconcile_name'
    _order = 'transaction_date desc'

    display_reconcile_name = fields.Char('Display Name', compute='_compute_display_reconcile_name',store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='provider_id.provider_type_id', readonly=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True)
    reconcile_lines_ids = fields.One2many('tt.reconcile.transaction.lines','reconcile_transaction_id','Line(s)')
    transaction_date = fields.Date('Transaction Date', readonly=True)
    state = fields.Selection([('open','Open')],'State', default='open', readonly=True)
    excel_file = fields.Binary('Excel File')
    total_lines = fields.Integer('Total Lines', compute='_compute_total_lines', store=True)
    currency_id = fields.Many2one('res.currency', 'Vendor Balance Currency',
                                  default=lambda self: self.env.user.company_id.currency_id,
                                  readonly=True)
    start_balance = fields.Monetary('Start Balance')
    end_balance = fields.Monetary('End Balance')

    @api.depends('provider_id','transaction_date')
    def _compute_display_reconcile_name(self):
        for rec in self:
            rec.display_reconcile_name = '%s %s' % (
                rec.provider_id and rec.provider_id.name or '',
                rec.transaction_date and datetime.strftime(rec.transaction_date,'%Y-%m-%d')
            )

    @api.depends('reconcile_lines_ids')
    def _compute_total_lines(self):
        for rec in self:
            rec.total_lines = len(rec.reconcile_lines_ids)

    def compare_reissue_recon_data(self, vals):
        return []

    def compare_reconcile_data(self,ctx=False,notif_to_telegram=False):
        if not self.env.user.has_group('tt_base.group_reconcile_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 91')
        not_match_str = ''
        idx = 1
        for rec in self.reconcile_lines_ids.filtered(lambda x: x.state == 'not_match'):
            found_rec = []
            if rec.type == 'reissue':
                found_rec = self.compare_reissue_recon_data({
                    'pnr': rec.pnr,
                    'total': abs(rec.total)
                })
            elif rec.type == 'nta':
                found_rec = self.env['tt.provider.%s' % (self.provider_type_id.code)].search([('pnr','=',rec.pnr),
                                                                                              ('total_price','=',abs(rec.total)),
                                                                                              ('reconcile_line_id','=',False)],limit=1)

                ##kalau tidak ketemu di provider masing masing cari di offline
                if not found_rec:
                    found_rec = self.env['tt.provider.offline'].search([('pnr', '=', rec.pnr),
                                                                        ('total_price', '=', abs(rec.total)),
                                                                        ('reconcile_line_id', '=',False)], limit=1)

                if not found_rec: #still not found after provider online & offline
                    found_rec = self.compare_reissue_recon_data({
                        'pnr': rec.pnr,
                        'total': abs(rec.total)
                    })

                ##kalau tidak ketemu juga, cari di reschedule
                # if not found_rec:
                #     found_rec = self.compare_reissue_recon_data({
                #         'pnr': rec.pnr,
                #         'total': abs(rec.total)
                #     })

            elif rec.type == 'refund':  # kata mba desi: kalo real amount lebih dari yang sebenarnya, dkurangi. Kalo real amount kurang, sisanya masuk pendapatan kantor
                found_rec = self.env['tt.refund'].search([('referenced_pnr', '=', rec.pnr),
                                                          ('state', '=', 'final'),
                                                          ('reconcile_line_id', '=', False)], limit=1)

            if found_rec:
                rec.write({
                    'res_model': found_rec[0]._name,
                    'res_id': found_rec[0].id,
                    'state': 'match'
                })
                found_rec[0].write({
                    'reconcile_line_id': rec.id,
                    'reconcile_time': datetime.now()
                })
                if found_rec[0]._name == 'tt.refund' and abs(rec.total) < found_rec[0].real_refund_amount:
                    divided_total = abs(rec.total) / len(found_rec[0].refund_line_ids)
                    for rec2 in found_rec[0].refund_line_ids:
                        rec2.write({
                            'real_refund_amount': divided_total
                        })
            else:
                if notif_to_telegram:
                    not_match_str += "{:03d}. {} Total Price: Rp {:,}\n\n".format(idx,rec['pnr'],rec['total'])
                    idx += 1

        if not_match_str:
            try:
                data = {
                    'code': 9909,
                    'message': 'Issued in Vendor not found/issued in system:\n%s\n%s' %(self.transaction_date,not_match_str),
                    'provider': self.provider_id.name,
                }
                self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data,
                                                               'notification_code')
            except Exception as e:
                _logger.error('Notification Compare Data Reconcile.\n %s' % (traceback.format_exc()))

    def find_unreconciled_reservation(self, start_date=False, end_date=False):
        # TODO: pertimbangkan apakah state booked or etc diperhitungkan juga
        state_list = ['issued', 'refund', 'reschedule']
        need_to_check = {}
        # CTH: klo state issued dia pakai issued date, klo state booking kita pakai booking date e dkk
        for rec in self.env['tt.provider.%s' % (self.provider_type_id.code)].search([('reconcile_line_id', '=', False),('state','in',state_list),
                                                                                     ('provider_id','=', self.provider_id.id),
                                                                                     ('issued_date','>=',start_date.replace(hour=0,minute=0,second=0).astimezone(pytz.UTC)),
                                                                                     ('issued_date' ,'<=',end_date.replace(hour=23,minute=59,second=59).astimezone(pytz.UTC))]):
            issued_date = str(rec.issued_date.astimezone(pytz.timezone('Asia/Jakarta')))[:10]
            if not need_to_check.get(issued_date):
                need_to_check[issued_date] = []
            need_to_check[issued_date].append({
                'order_number': rec.booking_id.name,
                'pnr': rec.pnr,
                'provider': rec.provider_id.name,
                'total_price': rec.total_price
            })
        return need_to_check

    def find_exist_in_vendor_only_reservation(self, start_date=False, end_date=False):
        need_to_check = {'in_range': {}, 'out_range': {}}
        for rec in self.reconcile_lines_ids.filtered(lambda x: x.state == 'not_match' and x.type == 'nta'):
            resv_date = rec.issued_time
            # Filter apakah provider_booking diatas masuk dalam range tanggal yg mau kita proses?
            if start_date <= resv_date.date() <= end_date:
                resv_type_by_date = 'in_range'
            else:
                resv_type_by_date = 'out_range'
                continue  # Remark baris ini jika pingin di notif untuk data yg out range

            if not need_to_check[resv_type_by_date].get(str(resv_date)[:10]):
                need_to_check[resv_type_by_date][str(resv_date)[:10]] = []
            need_to_check[resv_type_by_date][str(resv_date)[:10]].append({
                'order_number': '',
                'pnr': rec.pnr,
                'provider': rec.reconcile_transaction_id.provider_id.name,
            })
        return need_to_check

    def ntc_to_str(self, need_to_check):
        return_str = ''
        for date,pnr_list in need_to_check.items():
            return_str += date + ':\n'
            for idx, rec in enumerate(pnr_list):
                return_str += "{:03d}. {} ({}) Provider: {}\nTotal Price: Rp {:,}\n\n".format(idx+1,rec['order_number'],rec['pnr'],rec['provider'],rec['total_price'])
        return return_str

    def view_filter_tree(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 92')
        tree_id = self.env.ref('tt_reservation.tt_reconcile_transaction_lines_tree_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issued Reconcile Line(s)',
            'res_model': 'tt.reconcile.transaction.lines',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': tree_id.id,
            'context': {},
            'domain': [('reconcile_transaction_id', '=', self.id)],
            'target': 'current',
        }

    def print_report_excel(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 93')
        datas = {'id': self.id}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        url = self.env['tt.report.printout.reconcile'].print_report_excel(datas)
        self.excel_file = base64.encodebytes(url['value'])
        return url

    def multi_sync_balance(self):
        for rec in self[::-1]:
            rec.action_sync_balance()

    def action_sync_balance(self):
        reconcile_obj = self.env['tt.reconcile.transaction'].search([('provider_id', '=', self.provider_id.id),
                                                                     ('transaction_date', '<', self.transaction_date)],
                                                                    order='transaction_date desc', limit=1)

        if reconcile_obj and (self.transaction_date - reconcile_obj.transaction_date).days == 1 and self.provider_id.is_using_balance:
            self.start_balance = reconcile_obj.end_balance
            end_balance = self.start_balance

            for line in self.reconcile_lines_ids:
                if line.state == 'cancel':
                    continue
                elif line.type in ['nta', 'admin_bank', 'reissue', 'other','reversal_top_up']:
                    end_balance -= line.total
                else:
                    end_balance += line.total

            self.end_balance = end_balance
        else:
            self.start_balance = 0
            self.end_balance = 0


class TtReconcileTransactionLines(models.Model):
    _name = 'tt.reconcile.transaction.lines'
    _description = 'Reconcile Lines'
    _rec_name = 'pnr'

    reconcile_transaction_id = fields.Many2one('tt.reconcile.transaction','Reconcile Transaction',readonly=True, ondelete='cascade' )
    provider_type_code = fields.Char('Provider Type',related='reconcile_transaction_id.provider_type_id.code',readonly=True)
    agent_name = fields.Char('Agent Name',readonly=True)
    pnr = fields.Char('PNR',readonly=True)
    transaction_code = fields.Char('Transaction Code',readonly=True)
    type = fields.Selection([('nta','NTA'),
                             ('insentif','Insentif'),# saldo bertambah
                             ('refund_ssr','Refund SSR'),# saldo bertambah
                             ('top_up','Top Up'),# saldo bertambah
                             ('admin_bank','Admin Fee Bank'),# saldo berkurang
                             ('refund','Refund'),# saldo bertambah
                             ('reissue','ReIssue'),# saldo berkurang
                             ('reissue_ssr','ReIssue SSR'),# saldo berkurang
                             ('reversal','Reversal'),# saldo bertambah
                             ('reversal_top_up','Reversal Top Up'),# saldo berkurang
                             ('other','Other')],'Type', readonly=True)
    booking_time = fields.Datetime('Booking Time',readonly=True)
    issued_time = fields.Datetime('Issued Time',readonly=True)
    base_price = fields.Monetary('Base Price', readonly=True, currency_field='currency_id')
    tax = fields.Monetary('Tax',readonly=True, currency_field='currency_id')
    commission = fields.Monetary('Commission',readonly=True, currency_field='currency_id')
    total = fields.Monetary('Total Price',readonly=True, currency_field='currency_id')
    vendor_start_balance = fields.Monetary('Vendor Start Balance', readonly=True,
                                           currency_field='vendor_balance_currency_id')
    vendor_end_balance = fields.Monetary('Vendor End Balance', readonly=True,
                                         currency_field='vendor_balance_currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id,
                                  readonly=True)
    vendor_balance_currency_id = fields.Many2one('res.currency', 'Vendor Balance Currency',
                                                 default=lambda self: self.env.user.company_id.currency_id,
                                                 readonly=True)
    ticket_numbers = fields.Text('Ticket',readonly=True)
    description = fields.Text('Description',readonly=True)

    state = fields.Selection([('not_match','Not Match'),
                              ('match','Match'),
                              ('done','Done'),
                              ('ignore','Ignored'),
                              ('cancel','Cancelled')],'State',default='not_match',readonly=True)
    res_model = fields.Char('Ref Model', readonly=True)
    res_id = fields.Integer('Ref ID', readonly=True)

    sequence = fields.Integer('Sequence')

    def open_reference(self):
        # try:
        #     form_id = self.env[self.res_model].get_form_id()
        # except:
        form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
        form_id = form_id[0] if form_id else False


        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def get_default_state(self):
        if self.type in ['nta', 'refund', 'reissue']:
            self.state = 'not_match'
        else:
            self.state = 'done'

    def ignore_recon_line_from_button(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 94')
        if self.state == 'not_match':
            self.state = 'ignore'
        else:
            raise UserError('Can only ignore [Not Match] state.')

    def unignore_recon_line_from_button(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 95')
        if self.state == 'ignore':
            self.get_default_state()
        else:
            raise UserError('Can only unignore [Ignored] state.')

    def cancel_recon_line_from_button(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 96')
        if self.state != 'cancel':
            self.state = 'cancel'
        else:
            raise UserError('This line is already [Cancelled].')

    def uncancel_recon_line_from_button(self):
        if not self.env.user.has_group('tt_base.group_reconcile_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.. Code: 97')
        if self.state == 'cancel':
            self.get_default_state()
        else:
            raise UserError('Can only uncancel [Cancelled] state.')


class PrintoutReconcile(models.AbstractModel):
    _name = 'tt.report.printout.reconcile'
    _description = 'Report Printout Reconcile'

    @staticmethod
    def _select():
        return """
        rt.ticket_numbers, rt.agent_name, rt.pnr, rt.transaction_code, rt.type, rt.booking_time, rt.issued_time, rt.state, rt.base_price,
        rt.tax, rt.commission, rt.vendor_start_balance, rt.vendor_end_balance, rt.total, rt.description
        """

    @staticmethod
    def _from():
        return """
        tt_reconcile_transaction_lines rt
        """

    @staticmethod
    def _where(reconcile_id):
        where = "rt.reconcile_transaction_id = " + str(reconcile_id)
        return where

    @staticmethod
    def _group_by():
        return """
        rt.id
        """

    @staticmethod
    def _order_by():
        return """
        rt.id
        """

    def _lines(self, data):
        query = 'SELECT ' + self._select() + \
                'FROM ' + self._from() + \
                'WHERE ' + self._where(data['id']) + \
                'ORDER BY ' + self._order_by()
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    @staticmethod
    def ticket_to_list(ticket):
        if ticket:
            ticket_list = ticket.split('\n')
            # Remove empty string
            while '' in ticket_list:
                ticket_list.remove('')
            return ticket_list
        else:
            ticket = ['']
            return ticket

    def prepare_values(self, data):
        lines = self._lines(data)
        # for line in lines:
        #     line['ticket_numbers'] = self.ticket_to_list(line['ticket_numbers'])
        data['subtitle'] = 'Reconcile Report: '

        return {
            'lines': lines,
            'data': data
        }

    def print_report_excel(self, data):
        values = self.prepare_values(data)

        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        sheet_name = 'Reconcile Report'  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        user_tz = pytz.timezone('Asia/Jakarta')
        date_now = fields.datetime.now(tz=user_tz)

        # ======= TITLE, SUBTITLE & FILENAME ============
        filename = 'Reconcile Report ' + values['data']['form']['display_reconcile_name']
        filename_str = filename.replace(' ','_')

        sheet.merge_range('A1:L2', 'Reconcile Report', style.title)  # set merge cells for agent name
        sheet.merge_range('A3:L4', values['data']['form']['display_reconcile_name'], style.title2)  # set merge cells for title
        sheet.write('P5', 'Printing Date :' + date_now.strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'PNR', style.table_head_center)
        sheet.write('B9', 'Agent Name', style.table_head_center)
        sheet.write('C9', 'Transaction Code', style.table_head_center)
        sheet.write('D9', 'Type', style.table_head_center)
        sheet.write('E9', 'Booking Time', style.table_head_center)
        sheet.write('F9', 'Issued Time', style.table_head_center)
        sheet.write('G9', 'Base Price', style.table_head_center)
        sheet.write('H9', 'Tax', style.table_head_center)
        sheet.write('I9', 'Commission', style.table_head_center)
        sheet.write('J9', 'Total Price', style.table_head_center)
        sheet.write('K9', 'Vendor Start Balance', style.table_head_center)
        sheet.write('L9', 'Vendor End Balance', style.table_head_center)
        sheet.write('M9', 'State', style.table_head_center)
        sheet.write('N9', 'Ticket Numbers', style.table_head_center)
        sheet.write('O9', 'Description', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 13)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 19)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 18)
        sheet.set_column('F:F', 18)
        sheet.set_column('G:G', 17)
        sheet.set_column('H:H', 17)
        sheet.set_column('I:I', 17)
        sheet.set_column('J:J', 17)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 17)
        sheet.set_column('N:N', 50)
        sheet.set_column('O:O', 30)

        row_data = 8
        for rec in values['lines']:
            # Style
            row_data += 1

            sty_table_data_center = style.table_data_center
            sty_table_data = style.table_data
            sty_datetime = style.table_data_datetime
            sty_date = style.table_data_date
            sty_amount = style.table_data_amount

            if rec['state'] == 'match':
                sty_table_data_center = style.table_data_center_green
                sty_table_data = style.table_data_green
                sty_datetime = style.table_data_datetime_green
                sty_date = style.table_data_datetime_green
                sty_amount = style.table_data_amount_green
            elif rec['state'] == 'done':
                sty_table_data_center = style.table_data_center_blue
                sty_table_data = style.table_data_blue
                sty_datetime = style.table_data_datetime_blue
                sty_date = style.table_data_datetime_blue
                sty_amount = style.table_data_amount_blue
            elif rec['state'] == 'ignore':
                sty_table_data_center = style.table_data_center_orange
                sty_table_data = style.table_data_orange
                sty_datetime = style.table_data_datetime_orange
                sty_date = style.table_data_datetime_orange
                sty_amount = style.table_data_amount_orange
            elif rec['state'] == 'cancel':
                sty_table_data_center = style.table_data_center_red
                sty_table_data = style.table_data_red
                sty_datetime = style.table_data_datetime_red
                sty_date = style.table_data_datetime_red
                sty_amount = style.table_data_amount_red

            if row_data % 2 == 0:  # row genap : bg abu2
                sty_table_data_center = style.table_data_center_even
                sty_table_data = style.table_data_even
                sty_datetime = style.table_data_datetime_even
                sty_date = style.table_data_date_even
                sty_amount = style.table_data_amount_even

                if rec['state'] == 'match':
                    sty_table_data_center = style.table_data_center_green_even
                    sty_table_data = style.table_data_green_even
                    sty_datetime = style.table_data_datetime_green_even
                    sty_date = style.table_data_datetime_green_even
                    sty_amount = style.table_data_amount_green_even
                elif rec['state'] == 'done':
                    sty_table_data_center = style.table_data_center_blue_even
                    sty_table_data = style.table_data_blue_even
                    sty_datetime = style.table_data_datetime_blue_even
                    sty_date = style.table_data_datetime_blue_even
                    sty_amount = style.table_data_amount_blue_even
                elif rec['state'] == 'ignore':
                    sty_table_data_center = style.table_data_center_orange_even
                    sty_table_data = style.table_data_orange_even
                    sty_datetime = style.table_data_datetime_orange_even
                    sty_date = style.table_data_datetime_orange_even
                    sty_amount = style.table_data_amount_orange_even
                elif rec['state'] == 'cancel':
                    sty_table_data_center = style.table_data_center_red_even
                    sty_table_data = style.table_data_red_even
                    sty_datetime = style.table_data_datetime_red_even
                    sty_date = style.table_data_datetime_red_even
                    sty_amount = style.table_data_amount_red_even

            sty_table_data_center.font_size = 10
            sty_table_data.font_size = 10
            sty_datetime.font_size = 10
            sty_date.font_size = 10
            sty_amount.font_size = 10

            # Content
            sheet.write(row_data, 0, rec['pnr'], sty_table_data)
            sheet.write(row_data, 1, rec['agent_name'], sty_table_data)
            sheet.write(row_data, 2, rec['transaction_code'], sty_table_data)
            sheet.write(row_data, 3, rec['type'], sty_table_data)
            sheet.write(row_data, 4,
                        rec['booking_time'].astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if rec[
                            'booking_time'] else '',
                        sty_datetime)
            sheet.write(row_data, 5,
                        rec['issued_time'].astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if rec[
                            'issued_time'] else '',
                        sty_datetime)
            sheet.write(row_data, 6, rec['base_price'], sty_amount)
            sheet.write(row_data, 7, rec['tax'], sty_amount)
            sheet.write(row_data, 8, rec['commission'], sty_amount)
            sheet.write(row_data, 9, rec['total'], sty_amount)
            sheet.write(row_data, 10, rec['vendor_start_balance'], sty_amount)
            sheet.write(row_data, 11, rec['vendor_end_balance'], sty_amount)
            sheet.write(row_data, 12, rec['state'], sty_table_data)
            sheet.write(row_data, 13, rec['ticket_numbers'], sty_table_data)
            sheet.write(row_data, 14, rec['description'], sty_table_data)

        workbook.close()

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=tt.reconcile.transaction&field=excel_file&download=true&id=%s&filename=%s.xlsx' % (data['id'], filename_str),
            'target': 'new',
            'value': stream.getvalue()
        }
