from odoo import api,fields,models
from datetime import datetime
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
    usage_quota = fields.Integer('Usage Quota', compute='_compute_usage_quota',store=True) ## quota external
    amount = fields.Integer('Amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    price_package_id = fields.Many2one('tt.pnr.quota.price.package', 'Price Package')
    start_date = fields.Date('Start')
    expired_date = fields.Date('Valid Until', store=True)
    usage_ids = fields.One2many('tt.pnr.quota.usage', 'pnr_quota_id','Quota Usage', readonly=True, domain=['|',('active', '=', True),('active', '=', False)])
    agent_id = fields.Many2one('tt.agent','Agent', domain="[('is_using_pnr_quota','=',True)]")
    state = fields.Selection([('active', 'Active'), ('waiting', 'Waiting'), ('done', 'Done'), ('failed', 'Failed')], 'State',compute="_compute_state",store=True)
    transaction_amount_internal = fields.Monetary('Transaction Amount Internal', copy=False, readonly=True)
    transaction_amount_external = fields.Monetary('Transaction Amount External', copy=False, readonly=True)
    total_amount = fields.Monetary('Total Amount', copy=False, readonly=True)

    excel_file = fields.Binary('Excel File')

    @api.model
    def create(self, vals_list):
        package_obj = self.env['tt.pnr.quota.price.package'].browse(vals_list['price_package_id'])
        if package_obj:
            exp_date = datetime.now() + relativedelta(months=package_obj.validity)
            now = datetime.now(pytz.timezone('Asia/Jakarta'))
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota')
            vals_list['expired_date'] = "%s-%s-%s" % (exp_date.year, exp_date.month, calendar.monthrange(exp_date.year, exp_date.month)[1])
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

    @api.onchange('usage_ids', 'usage_ids.active')
    @api.depends('usage_ids', 'usage_ids.active')
    def _compute_usage_quota(self):
        for rec in self:
            usage_pnr = 0
            for usage_obj in rec.usage_ids.filtered(lambda x: x.inventory == 'external'):
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
            if rec.price_package_id.fix_profit_share == False:
                if rec.transaction_amount_internal > minimum:
                    rec.total_amount = rec.transaction_amount_external
                else:
                    rec.total_amount = minimum - rec.transaction_amount_internal + rec.transaction_amount_external
            else:
                rec.total_amount = minimum + rec.transaction_amount_external

    def payment_pnr_quota_api(self):
        for rec in self:
            if rec.agent_id.balance >= rec.total_amount:
                # bikin ledger
                self.env['tt.ledger'].create_ledger_vanilla(rec._name,
                                                            rec.id,
                                                            'Order: %s' % (rec.name),
                                                            rec.name,
                                                            datetime.now(pytz.timezone('Asia/Jakarta')).date(),
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
                                                            datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                                                            2,
                                                            rec.currency_id.id,
                                                            self.env.user.id,
                                                            self.env.ref('tt_base.rodex_ho').id,
                                                            False,
                                                            debit=rec.total_amount,
                                                            credit=0,
                                                            description='Buying PNR Quota for %s' % (rec.agent_id.name)
                                                            )
                rec.state = 'done'


    def get_pnr_quota_api(self,data,context):
        try:
            print(json.dumps(data))
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
                'price_package_id': price_package_obj.id
            })

            agent_obj.unban_user_api()

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
                        if price_list_obj.price_type == 'pnr':
                            price += price_list_obj.price * len(pnr)
                            try:
                                quota_pnr_usage += len(pnr) * req.get('ref_pax')
                            except:
                                try:
                                    quota_pnr_usage += len(pnr) * req.ref_pax  # recalculate
                                except:
                                    pass
                        elif price_list_obj.price_type == 'r/n':
                            try:
                                price += price_list_obj.price * req.get('ref_r_n')  # dari api
                                quota_pnr_usage += req.get('ref_r_n')
                            except:
                                price += price_list_obj.price * req.ref_r_n  # recalculate
                                quota_pnr_usage += req.ref_r_n  # recalculate
                        elif price_list_obj.price_type == 'pax':
                            try:
                                price += price_list_obj.price * req.get('ref_pax')  # dari api
                                quota_pnr_usage += req.get('ref_pax')  # dari api
                            except:
                                price += price_list_obj.price * req.ref_pax  # recalculate
                                quota_pnr_usage += req.ref_pax  # recalculate
                    else:
                        price_add = True
                        for carrier in carriers:
                            if price_list_obj.carrier_access_type == 'restrict' and price_list_obj.carrier_id.name == carrier or price_list_obj.carrier_id.name != carrier:
                                price_add = False
                        if price_add == True:
                            if price_list_obj.price_type == 'pnr':
                                price += price_list_obj.price * len(pnr)
                                try:
                                    quota_pnr_usage += len(pnr) * req.get('ref_pax')
                                except:
                                    try:
                                        quota_pnr_usage += len(pnr) * req.ref_pax  # recalculate
                                    except:
                                        pass
                            elif price_list_obj.price_type == 'r/n':
                                try:
                                    price += price_list_obj.price * req.get('ref_r_n') #dari api
                                    quota_pnr_usage += req.get('ref_r_n') #dari api
                                except:
                                    price += price_list_obj.price * req.ref_r_n  # recalculate
                                    quota_pnr_usage += req.ref_r_n  # recalculate
                            elif price_list_obj.price_type == 'pax':
                                try:
                                    price += price_list_obj.price * req.get('ref_pax') #dari api
                                    quota_pnr_usage += req.get('ref_pax') #dari api
                                except:
                                    price += price_list_obj.price * req.ref_pax #recalculate
                                    quota_pnr_usage += req.ref_pax #recalculate
        return {
            "price": price,
            "quota_pnr_usage": quota_pnr_usage
        }

    def recompute_wrong_value_amount(self):
        self.amount = int(self.price_package_id.minimum_fee)
        package_obj = self.price_package_id
        free_pnr_quota = package_obj.free_usage
        quota_pnr_usage = 0
        for rec in self.usage_ids.filtered(lambda x: x.inventory == 'external')[::-1]: ## reverse paling bawah duluan agar urutan free pnr tidak berubah
            ##check free juga
            calculate_price_dict = self.calculate_price(package_obj.available_price_list_ids, rec)
            rec.usage_quota = calculate_price_dict['quota_pnr_usage']
            if free_pnr_quota > quota_pnr_usage + calculate_price_dict['quota_pnr_usage']:
                rec.amount = 0
            elif free_pnr_quota > quota_pnr_usage:
                rec.amount = ((quota_pnr_usage + calculate_price_dict['quota_pnr_usage'] - free_pnr_quota) / calculate_price_dict['quota_pnr_usage']) * calculate_price_dict['price']
            else:
                rec.amount = calculate_price_dict['price']
            rec.usage_quota = calculate_price_dict['quota_pnr_usage']
            quota_pnr_usage += calculate_price_dict['quota_pnr_usage']

    def print_report_excel(self):
        datas = {'id': self.id}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        url = self.env['tt.report.printout.pnr.quota.usage'].print_report_excel(datas)
        self.sudo().excel_file = base64.encodebytes(url['value'])
        return url

class PrintoutPnrQuotaUsage(models.AbstractModel):
    _name = 'tt.report.printout.pnr.quota.usage'
    _description = 'Report Printout PNR Quota Usage'

    @staticmethod
    def _select():
        return """
        ref_name, ref_carriers, ref_pnrs, ref_pax, ref_r_n, inventory, amount,create_date
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
        sheet.write('F9', 'Room/Night', style.table_head_center)
        sheet.write('G9', 'Amount', style.table_head_center)
        sheet.write('H9', 'Type', style.table_head_center)

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
            sheet.write(row_data, 5, rec['ref_r_n'], sty_amount)
            sheet.write(row_data, 6, rec['amount'], sty_amount)
            sheet.write(row_data, 7, rec['inventory'], sty_table_data)

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
