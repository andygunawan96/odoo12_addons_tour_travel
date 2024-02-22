from odoo import api,fields,models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from ...tools import ERR
from ...tools.ERR import RequestException
import json,logging,traceback,pytz
import calendar,pytz
from dateutil.relativedelta import relativedelta
from io import BytesIO
import xlsxwriter, base64
from ...tools import tools_excel

_logger = logging.getLogger(__name__)

class TtPnrQuota(models.Model):
    _name = 'tt.pnr.quota'
    _rec_name = 'name'
    _description = 'PNR Quota'
    _order = 'id desc'

    name = fields.Char('Name')
    used_amount = fields.Integer('Total Transaction', compute='_compute_used_amount',store=True) ## harus nya total transaction
    total_passenger = fields.Integer('Total Passenger', compute='_compute_used_amount',store=True)
    total_room_night = fields.Integer('Total Room/Night', compute='_compute_used_amount',store=True)
    usage_quota = fields.Integer('Usage Quota', compute='_compute_usage_quota',store=True) ## quota external
    amount = fields.Integer('Amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    price_package_id = fields.Many2one('tt.pnr.quota.price.package', 'Price Package')
    start_date = fields.Date('Start')
    expired_date = fields.Date('Valid Until', store=True)
    usage_ids = fields.One2many('tt.pnr.quota.usage', 'pnr_quota_id','Quota Usage', readonly=True, domain=['|',('active', '=', True),('active', '=', False)])
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent','Agent', domain="[('is_using_pnr_quota','=',True)]")
    state = fields.Selection([('active', 'Active'), ('waiting', 'Waiting'), ('done', 'Done'), ('failed', 'Failed')], 'State',compute="_compute_state",store=True)
    transaction_amount_internal = fields.Monetary('Transaction Amount Internal', copy=False, readonly=True)
    transaction_amount_external = fields.Monetary('Transaction Amount External', copy=False, readonly=True)
    total_amount = fields.Monetary('Total Amount', copy=False, readonly=True)
    pnr_quota_excel_id = fields.Many2one('tt.upload.center', 'PNR Quota Excel', readonly=True)

    @api.model
    def create(self, vals_list):
        package_obj = self.env['tt.pnr.quota.price.package'].browse(vals_list['price_package_id'])
        if package_obj:
            exp_date = datetime.now() + relativedelta(months=package_obj.validity)
            now = datetime.now(pytz.timezone('Asia/Jakarta'))
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota')
            vals_list['expired_date'] = "%s-%s-01" % (exp_date.year, exp_date.month)
            vals_list['start_date'] = "%s-%s-%s" % (now.year, now.month, now.day)
            vals_list['state'] = 'active'
            vals_list['amount'] = int(package_obj.minimum_fee)
        else:
            raise Exception('Package not found')
        return super(TtPnrQuota, self).create(vals_list)

    @api.onchange('usage_ids', 'usage_ids.active')
    @api.depends('usage_ids', 'usage_ids.active')
    def _compute_used_amount(self):
        for rec in self:
            rec.used_amount = len(rec.usage_ids.ids)
            rec.total_passenger = sum(rec2.ref_pax for rec2 in rec.usage_ids)
            rec.total_room_night = sum(rec2.ref_r_n for rec2 in rec.usage_ids)


    @api.onchange('usage_ids', 'usage_ids.active')
    @api.depends('usage_ids', 'usage_ids.active')
    def _compute_usage_quota(self):
        for rec in self:
            usage_pnr = 0
            ## IVAN 9 NOV 2022 update usage_quota all inventory --> karena kebutuhan (bunga)
            for usage_obj in self.usage_ids[::-1]:  ## reverse paling bawah duluan agar urutan free pnr tidak berubah
                if rec.price_package_id.is_calculate_all_inventory or usage_obj.inventory == 'external':
                    usage_pnr += usage_obj.usage_quota
            rec.usage_quota = usage_pnr

    # @api.depends('price_list_id')
    # def _compute_amount(self):
    #     for rec in self:
    #         rec.amount = rec.price_list_id and rec.price_list_id.price or False

    # @api.depends('is_expired')
    # def _compute_state(self):
    #     for rec in self:
    #         if rec.is_expired:
    #             rec.state = 'expired'
    #         else:
    #             rec.state = 'active'

    # @api.onchange('agent_id')
    # def _onchange_domain_agent_id(self):
    #     return {'domain': {
    #         'price_list_id': [('id','in',self.agent_id.quota_package_id.available_price_list_ids.ids)]
    #     }}

    def to_dict(self):
        return {
            'name': self.name,
            'used_amount': self.used_amount,
            'usage_quota': self.usage_quota,
            'amount': self.amount,
            'expired_date': self.expired_date,
            'state': self.state
        }

    @api.onchange('min_amount', 'usage_ids')
    def calc_amount_internal(self):
        for rec in self:
            total_amount = 0
            for usage_obj in rec.usage_ids:
                if usage_obj.inventory == 'internal' and usage_obj.active:
                    total_amount += usage_obj.amount
            rec.transaction_amount_internal = total_amount

    @api.onchange('min_amount', 'usage_ids')
    def calc_amount_external(self):
        for rec in self:
            total_amount = 0
            for usage_obj in rec.usage_ids:
                if usage_obj.inventory == 'external' and usage_obj.active:
                    total_amount += usage_obj.amount
            rec.transaction_amount_external = total_amount

    @api.onchange('transaction_amount_internal', 'transaction_amount_external', 'usage_ids')
    def calc_amount_total(self):
        for rec in self:
            minimum = rec.amount
            if minimum == 0: #check jika minimum 0 ambil dari package
                rec.amount = rec.price_package_id.minimum_fee
                minimum = rec.price_package_id.minimum_fee
            total = rec.transaction_amount_external + rec.transaction_amount_internal
            if total > minimum:
                rec.total_amount = total
            else:
                rec.total_amount = minimum

    def payment_pnr_quota_api(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_pnr_quota_level_3').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 64')
        for rec in self:
            if rec.agent_id.is_payment_by_system and rec.agent_id.balance >= rec.total_amount:
                # bikin ledger
                self.env['tt.ledger'].create_ledger_vanilla(rec._name,
                                                            rec.id,
                                                            'Order: %s' % (rec.name),
                                                            rec.name,
                                                            2,
                                                            rec.currency_id.id,
                                                            self.env.user.id,
                                                            rec.agent_id.id,
                                                            False,
                                                            debit=0,
                                                            credit=rec.total_amount,
                                                            description='Buying PNR Quota for %s' % (rec.agent_id.name)
                                                            )
                self.env['tt.ledger'].create_ledger_vanilla(rec._name,
                                                            rec.id,
                                                            'Order: %s' % (rec.name),
                                                            rec.name,
                                                            2,
                                                            rec.currency_id.id,
                                                            self.env.user.id,
                                                            self.env.user.ho_id.id,
                                                            False,
                                                            debit=rec.total_amount,
                                                            credit=0,
                                                            description='Buying PNR Quota for %s' % (rec.agent_id.name)
                                                            )
                rec.state = 'done'
            else:
                rec.state = 'done'

    def set_to_waiting_pnr_quota(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_pnr_quota_level_3').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 65')
        ledgers_obj = self.ledger_ids.filtered(lambda x: x.is_reversed == False)
        for ledger_obj in ledgers_obj:
            ledger_obj.reverse_ledger()
        self.state = 'waiting'


    def get_pnr_quota_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            res = []
            dom = [('agent_id','=',agent_obj.id)]
            if data.get('state'):
                if data.get('state') != 'all':
                    dom.append(('state', '=', data['state']))

            for rec in self.search(dom):
                res.append(rec.to_dict())

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1012,additional_message="PNR Quota")

    def create_pnr_quota_api(self,req,context):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            price_package_obj = self.env['tt.pnr.quota.price.package'].search([('seq_id','=',req['quota_seq_id'])])
            try:
                price_package_obj.create_date
            except:
                raise RequestException(1032)

            # if agent_obj.balance < price_package_obj.price:
            #     raise RequestException(1007,additional_message='agent balance')

            new_pnr_quota = self.create({
                'agent_id': agent_obj.id,
                'ho_id': agent_obj.ho_id.id,
                'price_package_id': price_package_obj.id
            })

            agent_obj.unban_user_api()
            if req.get('is_called_from_backend'):
                return new_pnr_quota.id
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1031)

    def calculate_price(self, quota_list, req):
        price = 0
        quota_pnr_usage = 0
        type_price = 'pnr'
        try:
            carriers = req.get('ref_carriers').split(', ') # dari api
            pnr = req.get('ref_pnrs').split(', ') # dari api
        except:
            carriers = req.ref_carriers.split(', ') # recalculate
            pnr = req.ref_pnrs.split(', ')  # dari api
        for price_list_obj in quota_list:
            try:
                provider_type = req.get('ref_provider_type')
                provider = req.get('ref_provider')
            except:
                provider_type = req.ref_provider_type
                provider = req.ref_provider
            if provider_type == price_list_obj.provider_type_id.code:
                if price_list_obj.provider_access_type == 'all' or price_list_obj.provider_access_type == 'allow' and provider == price_list_obj.provider_id.code or price_list_obj.provider_access_type == 'restrict' and provider != price_list_obj.provider_id.code:
                    if price_list_obj.carrier_access_type == 'all':
                        price_add = True
                    else:
                        price_add = True
                        for carrier in carriers:
                            if price_list_obj.carrier_access_type == 'restrict' and price_list_obj.carrier_id.name == carrier or price_list_obj.carrier_id.name != carrier:
                                price_add = False
                    if price_add:
                        if price_list_obj.price_type == 'pnr':
                            price += price_list_obj.price * len(pnr)
                            type_price = 'pnr'
                            quota_pnr_usage += len(pnr)
                        elif price_list_obj.price_type == 'r/n':
                            type_price = 'r/n'
                            try:
                                price += price_list_obj.price * req.get('ref_r_n')  # dari api
                                quota_pnr_usage += req.get('ref_r_n')
                            except:
                                price += price_list_obj.price * req.ref_r_n  # recalculate
                                quota_pnr_usage += req.ref_r_n  # recalculate
                        elif price_list_obj.price_type == 'pax':
                            type_price = 'pax'
                            try:
                                price += price_list_obj.price * req.get('ref_pax')  # dari api
                                quota_pnr_usage += req.get('ref_pax')  # dari api
                            except:
                                price += price_list_obj.price * req.ref_pax  # recalculate
                                quota_pnr_usage += req.ref_pax  # recalculate
                        elif price_list_obj.price_type == 'pnr/pax':
                            type_price = 'pnr/pax'
                            try:
                                price += price_list_obj.price * (req.get('ref_pax') * len(pnr))  # dari api
                                quota_pnr_usage += (req.get('ref_pax') * len(pnr))  # dari api
                            except:
                                price += price_list_obj.price * (req.ref_pax * len(pnr))  # recalculate
                                quota_pnr_usage += (req.ref_pax * len(pnr))  # recalculate
        return {
            "price": price,
            "quota_pnr_usage": quota_pnr_usage,
            "type_price": type_price
        }

    def recompute_wrong_value_amount(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_pnr_quota_level_3').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 66')
        self.amount = int(self.price_package_id.minimum_fee)
        package_obj = self.price_package_id
        free_pnr_quota = package_obj.free_usage
        current_quota_pnr_usage = 0
        for usage_obj in self.usage_ids[::-1]: ## reverse paling bawah duluan agar urutan free pnr tidak berubah
            if package_obj.is_calculate_all_inventory or usage_obj.inventory == 'external':
                calculate_price_dict = self.calculate_price(package_obj.available_price_list_ids, usage_obj)
                ## check free
                if free_pnr_quota >= current_quota_pnr_usage + calculate_price_dict['quota_pnr_usage']:
                    usage_obj.amount = 0
                ## check quota pro rata
                elif free_pnr_quota > current_quota_pnr_usage and calculate_price_dict['type_price'] != 'pnr':
                    usage_obj.amount = ((current_quota_pnr_usage + calculate_price_dict['quota_pnr_usage'] - free_pnr_quota) / calculate_price_dict['quota_pnr_usage']) * calculate_price_dict['price']
                else:
                    usage_obj.amount = calculate_price_dict['price']
                usage_obj.usage_quota = calculate_price_dict['quota_pnr_usage']
                current_quota_pnr_usage += calculate_price_dict['quota_pnr_usage']
        self.usage_quota = current_quota_pnr_usage
        self.calc_amount_internal()
        self.calc_amount_external()
        self.calc_amount_total()


    def force_domain_agent_pnr_quota(self):
        return {
            'name': 'PNR Quota',
            'type': 'ir.actions.act_window',
            'res_model': 'tt.pnr.quota',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': ['|', ('agent_id', '=', self.env.user.agent_id.id), ('agent_id', 'in', self.env.user.agent_id.quota_partner_ids.ids)],
            'view_id': False,
            'views': [
                (self.env.ref('tt_base.tt_pnr_quota_tree_ho_view').id, 'tree'),
                (self.env.ref('tt_base.tt_pnr_quota_form_view').id, 'form'),
            ],
            'target': 'current'
        }

    def print_report_excel(self):
        datas = {'id': self.id}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res

        if self.agent_id:
            co_agent_id = self.agent_id.id
        else:
            co_agent_id = self.env.user.agent_id.id

        co_uid = self.env.user.id
        if not self.pnr_quota_excel_id:
            excel_bytes = self.env['tt.report.printout.pnr.quota.usage'].print_report_excel(datas)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': "PNR Quota Report %s.xlsx" % self.name,
                    'file_reference': 'PNR Quota',
                    'file': base64.b64encode(excel_bytes['value']),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.pnr_quota_excel_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.pnr_quota_excel_id.url,
            'path': self.pnr_quota_excel_id.path
        }
        return url

    def get_company_name(self):
        company_obj = self.env['res.company'].search([],limit=1)
        return company_obj.name

    def get_last_payment_date(self):
        date_str = "%s-15" % str(self.expired_date)[:7]
        return date_str

class PrintoutPnrQuotaUsage(models.AbstractModel):
    _name = 'tt.report.printout.pnr.quota.usage'
    _description = 'Report Printout PNR Quota Usage'

    @staticmethod
    def _select():
        return """
        ref_name, ref_carriers, ref_pnrs, ref_pax, usage_quota, ref_r_n, inventory, amount,create_date
        """

    @staticmethod
    def _from():
        return """
        tt_pnr_quota_usage
        """

    @staticmethod
    def _where(pnr_quota_id):
        where = "pnr_quota_id = " + str(pnr_quota_id)
        return where

    @staticmethod
    def _order_by():
        return """
        id
        """

    def _lines(self, data):
        query = 'SELECT ' + self._select() + \
                'FROM ' + self._from() + \
                'WHERE ' + self._where(data['id']) + \
                'ORDER BY ' + self._order_by()
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    def prepare_values(self, data):
        lines = self._lines(data)
        # for line in lines:
        #     line['ticket_numbers'] = self.ticket_to_list(line['ticket_numbers'])
        data['subtitle'] = 'PNR Quota Report: '

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

        sheet_name = 'PNR Quota Report'  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        user_tz = pytz.timezone('Asia/Jakarta')
        date_now = fields.datetime.now(tz=user_tz)

        # ======= TITLE, SUBTITLE & FILENAME ============
        filename = 'PNR Quota Report %s %s to %s' % (data['form']['agent_id'][1], data['form']['start_date'], data['form']['expired_date'])
        filename_str = filename.replace(' ','_')

        sheet.merge_range('A1:H2', 'PNR Quota Report', style.title)  # set merge cells for agent name
        sheet.merge_range('A3:H4', filename, style.title2)  # set merge cells for title
        sheet.write('H5', 'Printing Date :' + date_now.strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'Reference', style.table_head_center)
        sheet.write('B9', 'Date', style.table_head_center)
        sheet.write('C9', 'PNR', style.table_head_center)
        sheet.write('D9', 'Carriers', style.table_head_center)
        sheet.write('E9', 'Total Passengers', style.table_head_center)
        sheet.write('F9', 'Quota Usage', style.table_head_center)
        sheet.write('G9', 'Room/Night', style.table_head_center)
        sheet.write('H9', 'Amount', style.table_head_center)
        sheet.write('I9', 'Type', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 25)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 25)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 5)
        sheet.set_column('F:F', 5)
        sheet.set_column('G:G', 17)
        sheet.set_column('H:H', 17)
        sheet.set_column('I:I', 17)


        row_data = 8
        for rec in values['lines']:
            # Style
            row_data += 1

            if rec['inventory'] == 'internal':
                sty_table_data_center = style.table_data_center_green
                sty_table_data = style.table_data_green
                sty_datetime = style.table_data_datetime_green
                sty_date = style.table_data_datetime_green
                sty_amount = style.table_data_amount_green
            else:
                sty_table_data_center = style.table_data_center_blue
                sty_table_data = style.table_data_blue
                sty_datetime = style.table_data_datetime_blue
                sty_date = style.table_data_datetime_blue
                sty_amount = style.table_data_amount_blue

            if row_data % 2 == 0:  # row genap : bg abu2

                if rec['inventory'] == 'internal':
                    sty_table_data_center = style.table_data_center_green_even
                    sty_table_data = style.table_data_green_even
                    sty_datetime = style.table_data_datetime_green_even
                    sty_date = style.table_data_datetime_green_even
                    sty_amount = style.table_data_amount_green_even
                else:
                    sty_table_data_center = style.table_data_center_blue_even
                    sty_table_data = style.table_data_blue_even
                    sty_datetime = style.table_data_datetime_blue_even
                    sty_date = style.table_data_datetime_blue_even
                    sty_amount = style.table_data_amount_blue_even

            sty_table_data_center.font_size = 10
            sty_table_data.font_size = 10
            sty_datetime.font_size = 10
            sty_date.font_size = 10
            sty_amount.font_size = 10

            # Content
            sheet.write(row_data, 0, rec['ref_name'], sty_table_data)
            sheet.write(row_data, 1, rec['create_date'].astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S'),
                        sty_datetime)
            sheet.write(row_data, 2, rec['ref_pnrs'], sty_table_data)
            sheet.write(row_data, 3, rec['ref_carriers'], sty_table_data)
            sheet.write(row_data, 4, rec['ref_pax'], sty_amount)
            sheet.write(row_data, 5, rec['usage_quota'], sty_amount)
            sheet.write(row_data, 6, rec['ref_r_n'], sty_amount)
            sheet.write(row_data, 7, rec['amount'], sty_amount)
            sheet.write(row_data, 8, rec['inventory'], sty_table_data)

        sty_table_data = style.table_data
        sty_amount = style.table_data_amount
        sty_table_data_even = style.table_data_even
        sty_amount_even = style.table_data_amount_even

        row_data += 3
        sheet.write(row_data, 6, 'Minimum Amount', sty_table_data)
        sheet.write(row_data, 7, data['form']['amount'], sty_amount)
        sheet.write(row_data + 1, 6, 'Total Amount Internal', sty_table_data_even)
        sheet.write(row_data + 1, 7, data['form']['transaction_amount_internal'], sty_amount_even)
        sheet.write(row_data + 2, 6, 'Total Amount External', sty_table_data)
        sheet.write(row_data + 2, 7, data['form']['transaction_amount_external'], sty_amount)
        sheet.write(row_data + 3, 6, "Total Amount", sty_table_data_even)
        sheet.write(row_data + 3, 7, data['form']['total_amount'], sty_amount_even)

        workbook.close()

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=tt.pnr.quota&field=excel_file&download=true&id=%s&filename=%s.xlsx' % (data['id'], filename_str),
            'target': 'new',
            'value': stream.getvalue()
        }
