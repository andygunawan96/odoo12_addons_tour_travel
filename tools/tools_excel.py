import xlwt


class XlsxwriterStyle:
    def __init__(self, workbook):
        self.workbook = workbook

        self._table_data = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5})
        self._table_data_border = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1})
        self._table_data_even = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2'})
        self._table_data_even_border = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2', 'top': 1})

        self._table_data_center = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5})
        self._table_data_center_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_center_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2'})
        self._table_data_center_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top':1})

        self._table_data_center_red = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red'})
        self._table_data_center_red_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'top': 1})
        self._table_data_center_red_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red'})
        self._table_data_center_red_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red', 'top':1})

        self._table_data_right = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5})
        self._table_data_right_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_right_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2'})
        self._table_data_right_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'top':1})

        self._table_data_amount = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0'})
        self._table_data_amount_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'top': 1})
        self._table_data_amount_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0'})
        self._table_data_amount_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'top':1})

        self._table_data_amount_red = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red', 'top': 1})
        self._table_data_amount_red_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red', 'top': 1})

        self._table_data_datetime = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm', 'top':1})

        self._table_data_date = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._title = self.workbook.add_format({'align': 'center', 'valign' : 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 17.5, 'text_wrap': True})
        self._title2 = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 14, 'text_wrap': True})
        self._title_left = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 17.5})
        self._title2_left = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 14})

        self._table_head = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 8, 'border': 1, 'text_wrap': True})
        self._table_head1 = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 8, 'text_wrap': True})
        self._table_head_center = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'font_size': 8, 'font_color': 'white', 'bold': True, 'italic': False, 'pattern': 1, 'fg_color': '#F15A22', 'border': 1, 'text_wrap': True})
        self._table_head_date_right = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'font_size': 8, 'font_color': 'white', 'bold': True, 'italic': False, 'pattern': 1, 'fg_color': '#F15A22', 'border': 1})

        self._print_date = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'font_size': 9.5, 'bold': False, 'italic': True})
        self._caption = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'font_size': 9.5, 'bold': False, 'italic': True})
        self._title_consultant = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 10})

        self._table_data_group1 = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 9.5})

    @property
    def table_data(self):
        return self._table_data
    @property
    def table_data_border(self):
        return self._table_data_border
    @property
    def table_data_even(self):
        return self._table_data_even
    @property
    def table_data_even_border(self):
        return self._table_data_even_border

    @property
    def table_data_center(self):
        return self._table_data_center
    @property
    def table_data_center_border(self):
        return self._table_data_center_border
    @property
    def table_data_center_even(self):
        return self._table_data_center_even
    @property
    def table_data_center_even_border(self):
        return self._table_data_center_even_border

    @property
    def table_data_center_red(self):
        return self._table_data_center_red
    @property
    def table_data_center_red_border(self):
        return self._table_data_center_red_border
    @property
    def table_data_center_red_even(self):
        return self._table_data_center_red_even
    @property
    def table_data_center_red_even_border(self):
        return self._table_data_center_red_even_border

    @property
    def table_data_right(self):
        return self._table_data_right
    @property
    def table_data_right_border(self):
        return self._table_data_right_border
    @property
    def table_data_right_even(self):
        return self._table_data_right_even
    @property
    def table_data_right_even_border(self):
        return self._table_data_right_even_border

    @property
    def table_data_amount(self):
        return self._table_data_amount
    @property
    def table_data_amount_border(self):
        return self._table_data_amount_border
    @property
    def table_data_amount_even(self):
        return self._table_data_amount_even
    @property
    def table_data_amount_even_border(self):
        return self._table_data_amount_even_border

    @property
    def table_data_amount_red(self):
        return self._table_data_amount_red
    @property
    def table_data_amount_red_border(self):
        return self._table_data_amount_red_border
    @property
    def table_data_amount_red_even(self):
        return self._table_data_amount_red_even
    @property
    def table_data_amount_red_even_border(self):
        return self._table_data_amount_red_even_border

    @property
    def table_data_datetime(self):
        return self._table_data_datetime
    @property
    def table_data_datetime_border(self):
        return self._table_data_datetime_border
    @property
    def table_data_datetime_even(self):
        return self._table_data_datetime_even
    @property
    def table_data_datetime_even_border(self):
        return self._table_data_datetime_even_border

    @property
    def table_data_date(self):
        return self._table_data_date
    @property
    def table_data_date_border(self):
        return self._table_data_date_border
    @property
    def table_data_date_even(self):
        return self._table_data_date_even
    @property
    def table_data_date_even_border(self):
        return self._table_data_date_even_border

    @property
    def title(self):
        return self._title
    @property
    def title2(self):
        return self._title2

    @property
    def title_left(self):
        return self._title_left
    @property
    def title2_left(self):
        return self._title2_left

    @property
    def table_head(self):
        return self._table_head
    @property
    def table_head1(self):
        return self._table_head1
    @property
    def table_head_center(self):
        return self._table_head_center
    @property
    def table_head_date_right(self):
        return self._table_head_date_right

    @property
    def print_date(self):
        return self._print_date
    @property
    def caption(self):
        return self._caption
    @property
    def title_consultant(self):
        return self._title_consultant

    @property
    def table_data_group1(self):
        return self._table_data_group1