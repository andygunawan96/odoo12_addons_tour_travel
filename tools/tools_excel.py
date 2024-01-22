import xlwt


class XlsxwriterStyle:
    def __init__(self, workbook):
        self.workbook = workbook

        self._table_data = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5})
        self._table_data_bold = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5})
        self._table_data_wrap = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'text_wrap': True})
        self._table_data_border = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1})
        self._table_data_border_bold = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'top': 1})
        self._table_data_border_wrap = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1, 'text_wrap': True})
        self._table_data_total_footer = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'white', 'fg_color': '#205B95', 'top': 1})
        self._table_data_even = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2'})
        self._table_data_even_bold = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2'})
        self._table_data_even_wrap = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2', 'text_wrap': True})
        self._table_data_even_border = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2', 'top': 1})
        self._table_data_even_border_bold = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2', 'top': 1})
        self._table_data_even_border_wrap = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1,'fg_color': '#F2F2F2', 'top': 1, 'text_wrap': True})

        self._table_data_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red'})
        self._table_data_bold_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red'})
        self._table_data_border_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'red'})
        self._table_data_border_bold_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'red'})
        self._table_data_even_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red'})
        self._table_data_even_bold_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red'})
        self._table_data_even_border_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'red'})
        self._table_data_even_border_bold_red = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'red'})

        self._table_data_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green'})
        self._table_data_bold_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green'})
        self._table_data_border_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'green'})
        self._table_data_border_bold_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'green'})
        self._table_data_even_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green'})
        self._table_data_even_bold_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green'})
        self._table_data_even_border_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'green'})
        self._table_data_even_border_bold_green = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'green'})

        self._table_data_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue'})
        self._table_data_bold_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue'})
        self._table_data_border_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'blue'})
        self._table_data_border_bold_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'blue'})
        self._table_data_even_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue'})
        self._table_data_even_bold_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue'})
        self._table_data_even_border_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'blue'})
        self._table_data_even_border_bold_blue = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'blue'})

        self._table_data_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'orange'})
        self._table_data_bold_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'orange'})
        self._table_data_border_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'orange'})
        self._table_data_border_bold_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'top': 1, 'font_color': 'orange'})
        self._table_data_even_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange'})
        self._table_data_even_bold_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange'})
        self._table_data_even_border_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'orange'})
        self._table_data_even_border_bold_orange = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top': 1, 'font_color': 'orange'})

        self._table_data_center = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5})
        self._table_data_center_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5})
        self._table_data_center_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_center_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_center_total_footer = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'font_color': 'white', 'fg_color': '#205B95', 'top': 1})
        self._table_data_center_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2'})
        self._table_data_center_even_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2'})
        self._table_data_center_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top':1})
        self._table_data_center_even_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'top':1})

        self._table_data_center_red = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red'})
        self._table_data_center_red_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red'})
        self._table_data_center_red_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'top': 1})
        self._table_data_center_red_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'top': 1})
        self._table_data_center_red_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red'})
        self._table_data_center_red_even_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red'})
        self._table_data_center_red_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red', 'top':1})
        self._table_data_center_red_even_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'red', 'top':1})

        self._table_data_center_green = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green'})
        self._table_data_center_green_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green'})
        self._table_data_center_green_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'top': 1})
        self._table_data_center_green_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'top': 1})
        self._table_data_center_green_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'green'})
        self._table_data_center_green_even_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'green'})
        self._table_data_center_green_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'green', 'top': 1})
        self._table_data_center_green_even_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'green', 'top': 1})

        self._table_data_center_blue = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue'})
        self._table_data_center_blue_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue'})
        self._table_data_center_blue_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'top': 1})
        self._table_data_center_blue_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'top': 1})
        self._table_data_center_blue_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'blue'})
        self._table_data_center_blue_even_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'blue'})
        self._table_data_center_blue_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'top': 1})
        self._table_data_center_blue_even_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'top': 1})

        self._table_data_center_orange = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'font_color': 'orange'})
        self._table_data_center_orange_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'font_color': 'orange'})
        self._table_data_center_orange_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'font_color': 'orange', 'top': 1})
        self._table_data_center_orange_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'font_color': 'orange', 'top': 1})
        self._table_data_center_orange_even = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'orange'})
        self._table_data_center_orange_even_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'orange'})
        self._table_data_center_orange_even_border = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'top': 1})
        self._table_data_center_orange_even_border_bold = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'top': 1})

        self._table_data_right = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5})
        self._table_data_right_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5})
        self._table_data_right_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_right_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'top': 1})
        self._table_data_right_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2'})
        self._table_data_right_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2'})
        self._table_data_right_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'top':1})
        self._table_data_right_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'fg_color': '#F2F2F2', 'top':1})

        self._table_data_amount = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0'})
        self._table_data_amount_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0'})
        self._table_data_amount_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'top': 1})
        self._table_data_amount_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'top': 1})
        self._table_data_amount_total_footer = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'white', 'fg_color': '#205B95', 'num_format': '#,##0', 'top': 1, 'border': 1})
        self._table_data_amount_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0'})
        self._table_data_amount_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0'})
        self._table_data_amount_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'top':1})
        self._table_data_amount_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False,'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'top':1})

        self._table_data_amount_red = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red', 'top': 1})
        self._table_data_amount_red_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'red', 'top': 1})
        self._table_data_amount_red_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red'})
        self._table_data_amount_red_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red', 'top': 1})
        self._table_data_amount_red_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'red', 'top': 1})

        self._table_data_amount_green = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'green'})
        self._table_data_amount_green_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'green'})
        self._table_data_amount_green_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'green', 'top': 1})
        self._table_data_amount_green_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'green', 'top': 1})
        self._table_data_amount_green_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'green'})
        self._table_data_amount_green_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'green'})
        self._table_data_amount_green_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'green', 'top': 1})
        self._table_data_amount_green_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'green', 'top': 1})

        self._table_data_amount_blue = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'blue'})
        self._table_data_amount_blue_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'blue'})
        self._table_data_amount_blue_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'blue', 'top': 1})
        self._table_data_amount_blue_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'blue', 'top': 1})
        self._table_data_amount_blue_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'blue'})
        self._table_data_amount_blue_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'blue'})
        self._table_data_amount_blue_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'blue', 'top': 1})
        self._table_data_amount_blue_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'blue', 'top': 1})

        self._table_data_amount_orange = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'orange'})
        self._table_data_amount_orange_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'orange'})
        self._table_data_amount_orange_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'orange', 'top': 1})
        self._table_data_amount_orange_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': '#,##0', 'font_color': 'orange', 'top': 1})
        self._table_data_amount_orange_even = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'orange'})
        self._table_data_amount_orange_even_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'orange'})
        self._table_data_amount_orange_even_border = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'orange', 'top': 1})
        self._table_data_amount_orange_even_border_bold = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': '#,##0', 'font_color': 'orange', 'top': 1})

        self._table_data_datetime = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_border_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_total_footer = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'white', 'fg_color': '#205B95', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm', 'top':1})
        self._table_data_datetime_even_border_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy hh:mm', 'top':1})

        self._table_data_datetime_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_border_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_border_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})

        self._table_data_datetime_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_border_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_border_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})

        self._table_data_datetime_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_border_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_border_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})

        self._table_data_datetime_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False,'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_border_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_border_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm'})
        self._table_data_datetime_even_border_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})
        self._table_data_datetime_even_border_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy hh:mm', 'top': 1})

        self._table_data_date = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_border_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_total_footer = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'white', 'fg_color': '#205B95', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_border_bold = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._table_data_date_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_border_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'red', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_border_bold_red = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'red', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._table_data_date_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_border_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'green', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_border_bold_green = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'green', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._table_data_date_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_border_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_border_bold_blue = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'blue', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._table_data_date_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_border_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_border_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy'})
        self._table_data_date_even_border_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy', 'top': 1})
        self._table_data_date_even_border_bold_orange = self.workbook.add_format({'align': 'justify', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 7.5, 'pattern': 1, 'fg_color': '#F2F2F2', 'font_color': 'orange', 'num_format': 'dd-mmm-yyyy', 'top': 1})

        self._title = self.workbook.add_format({'align': 'center', 'valign' : 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 17.5, 'text_wrap': True})
        self._title2 = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 14, 'text_wrap': True})
        self._title_left = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 17.5})
        self._title2_left = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'bold': False, 'italic': False, 'font_size': 14})

        self._table_head = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 8, 'border': 1, 'text_wrap': True})
        self._table_head1 = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 8, 'text_wrap': True})
        self._table_head_center = self.workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_name': 'Calibri', 'font_size': 8, 'font_color': 'white', 'bold': True, 'italic': False, 'pattern': 1, 'fg_color': '#205B95', 'border': 1, 'text_wrap': True})
        self._table_head_date_right = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'font_size': 8, 'font_color': 'white', 'bold': True, 'italic': False, 'pattern': 1, 'fg_color': '#205B95', 'border': 1})

        self._print_date = self.workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_name': 'Calibri', 'font_size': 9.5, 'bold': False, 'italic': True})
        self._caption = self.workbook.add_format({'align': 'vcenter', 'font_name': 'Calibri', 'font_size': 9.5, 'bold': False, 'italic': True})
        self._title_consultant = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 10})

        self._table_data_group1 = self.workbook.add_format({'font_name': 'Calibri', 'bold': True, 'italic': False, 'font_size': 9.5})

    @property
    def table_data(self):
        return self._table_data
    @property
    def table_data_bold(self):
        return self._table_data_bold
    @property
    def table_data_wrap(self):
        return self._table_data_wrap
    @property
    def table_data_border(self):
        return self._table_data_border
    @property
    def table_data_border_bold(self):
        return self._table_data_border_bold
    @property
    def table_data_border_wrap(self):
        return self._table_data_border_wrap
    @property
    def table_data_total_footer(self):
        return self._table_data_total_footer
    @property
    def table_data_even(self):
        return self._table_data_even
    @property
    def table_data_even_bold(self):
        return self._table_data_even_bold
    @property
    def table_data_even_wrap(self):
        return self._table_data_even_wrap
    @property
    def table_data_even_border(self):
        return self._table_data_even_border
    @property
    def table_data_even_border_bold(self):
        return self._table_data_even_border_bold
    @property
    def table_data_even_border_wrap(self):
        return self._table_data_even_border_wrap

    @property
    def table_data_red(self):
        return self._table_data_red
    @property
    def table_data_red_bold(self):
        return self._table_data_bold_red
    @property
    def table_data_red_border(self):
        return self._table_data_border_red
    @property
    def table_data_red_border_bold(self):
        return self._table_data_border_bold_red
    @property
    def table_data_red_even(self):
        return self._table_data_even_red
    @property
    def table_data_red_even_bold(self):
        return self._table_data_even_bold_red
    @property
    def table_data_red_even_border(self):
        return self._table_data_even_border_red
    @property
    def table_data_red_even_border_bold(self):
        return self._table_data_even_border_bold_red

    @property
    def table_data_green(self):
        return self._table_data_green
    @property
    def table_data_green_bold(self):
        return self._table_data_bold_green
    @property
    def table_data_green_border(self):
        return self._table_data_border_green
    @property
    def table_data_green_border_bold(self):
        return self._table_data_border_bold_green
    @property
    def table_data_green_even(self):
        return self._table_data_even_green
    @property
    def table_data_green_even_bold(self):
        return self._table_data_even_bold_green
    @property
    def table_data_green_even_border(self):
        return self._table_data_even_border_green
    @property
    def table_data_green_even_border_bold(self):
        return self._table_data_even_border_bold_green

    @property
    def table_data_blue(self):
        return self._table_data_blue
    @property
    def table_data_blue_bold(self):
        return self._table_data_bold_blue
    @property
    def table_data_blue_border(self):
        return self._table_data_border_blue
    @property
    def table_data_blue_border_bold(self):
        return self._table_data_border_bold_blue
    @property
    def table_data_blue_even(self):
        return self._table_data_even_blue
    @property
    def table_data_blue_even_bold(self):
        return self._table_data_even_bold_blue
    @property
    def table_data_blue_even_border(self):
        return self._table_data_even_border_blue
    @property
    def table_data_blue_even_border_bold(self):
        return self._table_data_even_border_bold_blue

    @property
    def table_data_orange(self):
        return self._table_data_orange
    @property
    def table_data_orange_bold(self):
        return self._table_data_bold_orange
    @property
    def table_data_orange_border(self):
        return self._table_data_border_orange
    @property
    def table_data_orange_border_bold(self):
        return self._table_data_border_bold_orange
    @property
    def table_data_orange_even(self):
        return self._table_data_even_orange
    @property
    def table_data_orange_even_bold(self):
        return self._table_data_even_bold_orange
    @property
    def table_data_orange_even_border(self):
        return self._table_data_even_border_orange
    @property
    def table_data_orange_even_border_bold(self):
        return self._table_data_even_border_bold_orange

    @property
    def table_data_center(self):
        return self._table_data_center
    @property
    def table_data_center_bold(self):
        return self._table_data_center_bold
    @property
    def table_data_center_border(self):
        return self._table_data_center_border
    @property
    def table_data_center_border_bold(self):
        return self._table_data_center_border_bold
    @property
    def table_data_center_total_footer(self):
        return self._table_data_center_total_footer
    @property
    def table_data_center_even(self):
        return self._table_data_center_even
    @property
    def table_data_center_even_bold(self):
        return self._table_data_center_even_bold
    @property
    def table_data_center_even_border(self):
        return self._table_data_center_even_border
    @property
    def table_data_center_even_border_bold(self):
        return self._table_data_center_even_border_bold


    @property
    def table_data_center_red(self):
        return self._table_data_center_red
    @property
    def table_data_center_red_bold(self):
        return self._table_data_center_red_bold
    @property
    def table_data_center_red_border(self):
        return self._table_data_center_red_border
    @property
    def table_data_center_red_border_bold(self):
        return self._table_data_center_red_border_bold
    @property
    def table_data_center_red_even(self):
        return self._table_data_center_red_even
    @property
    def table_data_center_red_even_bold(self):
        return self._table_data_center_red_even_bold
    @property
    def table_data_center_red_even_border(self):
        return self._table_data_center_red_even_border
    @property
    def table_data_center_red_even_border_bold(self):
        return self._table_data_center_red_even_border_bold

    @property
    def table_data_center_green(self):
        return self._table_data_center_green
    @property
    def table_data_center_green_bold(self):
        return self._table_data_center_green_bold
    @property
    def table_data_center_green_border(self):
        return self._table_data_center_green_border
    @property
    def table_data_center_green_border_bold(self):
        return self._table_data_center_green_border_bold
    @property
    def table_data_center_green_even(self):
        return self._table_data_center_green_even
    @property
    def table_data_center_green_even_bold(self):
        return self._table_data_center_green_even_bold
    @property
    def table_data_center_green_even_border(self):
        return self._table_data_center_green_even_border
    @property
    def table_data_center_green_even_border_bold(self):
        return self._table_data_center_green_even_border_bold

    @property
    def table_data_center_blue(self):
        return self._table_data_center_blue
    @property
    def table_data_center_blue_bold(self):
        return self._table_data_center_blue_bold
    @property
    def table_data_center_blue_border(self):
        return self._table_data_center_blue_border
    @property
    def table_data_center_blue_border_bold(self):
        return self._table_data_center_blue_border_bold
    @property
    def table_data_center_blue_even(self):
        return self._table_data_center_blue_even
    @property
    def table_data_center_blue_even_bold(self):
        return self._table_data_center_blue_even_bold
    @property
    def table_data_center_blue_even_border(self):
        return self._table_data_center_blue_even_border
    @property
    def table_data_center_blue_even_border_bold(self):
        return self._table_data_center_blue_even_border_bold

    @property
    def table_data_center_orange(self):
        return self._table_data_center_orange
    @property
    def table_data_center_orange_bold(self):
        return self._table_data_center_orange_bold
    @property
    def table_data_center_orange_border(self):
        return self._table_data_center_orange_border
    @property
    def table_data_center_orange_border_bold(self):
        return self._table_data_center_orange_border_bold
    @property
    def table_data_center_orange_even(self):
        return self._table_data_center_orange_even
    @property
    def table_data_center_orange_even_bold(self):
        return self._table_data_center_orange_even_bold
    @property
    def table_data_center_orange_even_border(self):
        return self._table_data_center_orange_even_border
    @property
    def table_data_center_orange_even_border_bold(self):
        return self._table_data_center_orange_even_border_bold

    @property
    def table_data_right(self):
        return self._table_data_right
    @property
    def table_data_right_bold(self):
        return self._table_data_right_bold
    @property
    def table_data_right_border(self):
        return self._table_data_right_border
    @property
    def table_data_right_border_bold(self):
        return self._table_data_right_border_bold
    @property
    def table_data_right_even(self):
        return self._table_data_right_even
    @property
    def table_data_right_even_bold(self):
        return self._table_data_right_even_bold
    @property
    def table_data_right_even_border(self):
        return self._table_data_right_even_border
    @property
    def table_data_right_even_border_bold(self):
        return self._table_data_right_even_border_bold

    @property
    def table_data_amount(self):
        return self._table_data_amount
    @property
    def table_data_amount_bold(self):
        return self._table_data_amount_bold
    @property
    def table_data_amount_border(self):
        return self._table_data_amount_border
    @property
    def table_data_amount_border_bold(self):
        return self._table_data_amount_border_bold
    @property
    def table_data_amount_total_footer(self):
        return self._table_data_amount_total_footer
    @property
    def table_data_amount_even(self):
        return self._table_data_amount_even
    @property
    def table_data_amount_even_bold(self):
        return self._table_data_amount_even_bold
    @property
    def table_data_amount_even_border(self):
        return self._table_data_amount_even_border
    @property
    def table_data_amount_even_border_bold(self):
        return self._table_data_amount_even_border_bold

    @property
    def table_data_amount_red(self):
        return self._table_data_amount_red
    @property
    def table_data_amount_red_bold(self):
        return self._table_data_amount_red_bold
    @property
    def table_data_amount_red_border(self):
        return self._table_data_amount_red_border
    @property
    def table_data_amount_red_border_bold(self):
        return self._table_data_amount_red_border_bold
    @property
    def table_data_amount_red_even(self):
        return self._table_data_amount_red_even
    @property
    def table_data_amount_red_even_bold(self):
        return self._table_data_amount_red_even_bold
    @property
    def table_data_amount_red_even_border(self):
        return self._table_data_amount_red_even_border
    @property
    def table_data_amount_red_even_border_bold(self):
        return self.table_data_amount_red_even_border_bold

    @property
    def table_data_amount_green(self):
        return self._table_data_amount_green
    @property
    def table_data_amount_green_bold(self):
        return self._table_data_amount_green_bold
    @property
    def table_data_amount_green_border(self):
        return self._table_data_amount_green_border
    @property
    def table_data_amount_green_border_bold(self):
        return self._table_data_amount_green_border_bold
    @property
    def table_data_amount_green_even(self):
        return self._table_data_amount_green_even
    @property
    def table_data_amount_green_even_bold(self):
        return self._table_data_amount_green_even_bold
    @property
    def table_data_amount_green_even_border(self):
        return self._table_data_amount_green_even_border
    @property
    def table_data_amount_green_even_border_bold(self):
        return self.table_data_amount_green_even_border_bold

    @property
    def table_data_amount_blue(self):
        return self._table_data_amount_blue
    @property
    def table_data_amount_blue_bold(self):
        return self._table_data_amount_blue_bold
    @property
    def table_data_amount_blue_border(self):
        return self._table_data_amount_blue_border
    @property
    def table_data_amount_blue_border_bold(self):
        return self._table_data_amount_blue_border_bold
    @property
    def table_data_amount_blue_even(self):
        return self._table_data_amount_blue_even
    @property
    def table_data_amount_blue_even_bold(self):
        return self._table_data_amount_blue_even_bold
    @property
    def table_data_amount_blue_even_border(self):
        return self._table_data_amount_blue_even_border
    @property
    def table_data_amount_blue_even_border_bold(self):
        return self.table_data_amount_blue_even_border_bold

    @property
    def table_data_amount_orange(self):
        return self._table_data_amount_orange
    @property
    def table_data_amount_orange_bold(self):
        return self._table_data_amount_orange_bold
    @property
    def table_data_amount_orange_border(self):
        return self._table_data_amount_orange_border
    @property
    def table_data_amount_orange_border_bold(self):
        return self._table_data_amount_orange_border_bold
    @property
    def table_data_amount_orange_even(self):
        return self._table_data_amount_orange_even
    @property
    def table_data_amount_orange_even_bold(self):
        return self._table_data_amount_orange_even_bold
    @property
    def table_data_amount_orange_even_border(self):
        return self._table_data_amount_orange_even_border
    @property
    def table_data_amount_orange_even_border_bold(self):
        return self.table_data_amount_orange_even_border_bold

    @property
    def table_data_datetime(self):
        return self._table_data_datetime
    @property
    def table_data_datetime_bold(self):
        return self._table_data_datetime_bold
    @property
    def table_data_datetime_border(self):
        return self._table_data_datetime_border
    @property
    def table_data_datetime_border_bold(self):
        return self._table_data_datetime_border_bold
    @property
    def table_data_datetime_total_footer(self):
        return self._table_data_datetime_total_footer
    @property
    def table_data_datetime_even(self):
        return self._table_data_datetime_even
    @property
    def table_data_datetime_even_bold(self):
        return self._table_data_datetime_even_bold
    @property
    def table_data_datetime_even_border(self):
        return self._table_data_datetime_even_border
    @property
    def table_data_datetime_even_border_bold(self):
        return self._table_data_datetime_even_border_bold

    @property
    def table_data_datetime_red(self):
        return self._table_data_datetime_red
    @property
    def table_data_datetime_red_bold(self):
        return self._table_data_datetime_bold_red
    @property
    def table_data_datetime_red_border(self):
        return self._table_data_datetime_border_red
    @property
    def table_data_datetime_red_border_bold(self):
        return self._table_data_datetime_border_bold_red
    @property
    def table_data_datetime_red_even(self):
        return self._table_data_datetime_even_red
    @property
    def table_data_datetime_red_even_bold(self):
        return self._table_data_datetime_even_bold_red
    @property
    def table_data_datetime_red_even_border(self):
        return self._table_data_datetime_even_border_red
    @property
    def table_data_datetime_red_even_border_bold(self):
        return self._table_data_datetime_even_border_bold_red

    @property
    def table_data_datetime_green(self):
        return self._table_data_datetime_green
    @property
    def table_data_datetime_green_bold(self):
        return self._table_data_datetime_bold_green
    @property
    def table_data_datetime_green_border(self):
        return self._table_data_datetime_border_green
    @property
    def table_data_datetime_green_border_bold(self):
        return self._table_data_datetime_border_bold_green
    @property
    def table_data_datetime_green_even(self):
        return self._table_data_datetime_even_green
    @property
    def table_data_datetime_green_even_bold(self):
        return self._table_data_datetime_even_bold_green
    @property
    def table_data_datetime_green_even_border(self):
        return self._table_data_datetime_even_border_green
    @property
    def table_data_datetime_green_even_border_bold(self):
        return self._table_data_datetime_even_border_bold_green

    @property
    def table_data_datetime_blue(self):
        return self._table_data_datetime_blue
    @property
    def table_data_datetime_blue_bold(self):
        return self._table_data_datetime_bold_blue
    @property
    def table_data_datetime_blue_border(self):
        return self._table_data_datetime_border_blue
    @property
    def table_data_datetime_blue_border_bold(self):
        return self._table_data_datetime_border_bold_blue
    @property
    def table_data_datetime_blue_even(self):
        return self._table_data_datetime_even_blue
    @property
    def table_data_datetime_blue_even_bold(self):
        return self._table_data_datetime_even_bold_blue
    @property
    def table_data_datetime_blue_even_border(self):
        return self._table_data_datetime_even_border_blue
    @property
    def table_data_datetime_blue_even_border_bold(self):
        return self._table_data_datetime_even_border_bold_blue

    @property
    def table_data_datetime_orange(self):
        return self._table_data_datetime_orange
    @property
    def table_data_datetime_orange_bold(self):
        return self._table_data_datetime_bold_orange
    @property
    def table_data_datetime_orange_border(self):
        return self._table_data_datetime_border_orange
    @property
    def table_data_datetime_orange_border_bold(self):
        return self._table_data_datetime_border_bold_orange
    @property
    def table_data_datetime_orange_even(self):
        return self._table_data_datetime_even_orange
    @property
    def table_data_datetime_orange_even_bold(self):
        return self._table_data_datetime_even_bold_orange
    @property
    def table_data_datetime_orange_even_border(self):
        return self._table_data_datetime_even_border_orange
    @property
    def table_data_datetime_orange_even_border_bold(self):
        return self._table_data_datetime_even_border_bold_orange

    @property
    def table_data_date(self):
        return self._table_data_date
    @property
    def table_data_date_bold(self):
        return self._table_data_date_bold
    @property
    def table_data_date_border(self):
        return self._table_data_date_border
    @property
    def table_data_date_border_bold(self):
        return self._table_data_date_border_bold
    @property
    def table_data_date_total_footer(self):
        return self._table_data_date_total_footer
    @property
    def table_data_date_even(self):
        return self._table_data_date_even
    @property
    def table_data_date_even_bold(self):
        return self._table_data_date_even_bold
    @property
    def table_data_date_even_border(self):
        return self._table_data_date_even_border
    @property
    def table_data_date_even_border_bold(self):
        return self._table_data_date_even_border_bold

    @property
    def table_data_date_red(self):
        return self._table_data_date_red
    @property
    def table_data_date_red_bold(self):
        return self._table_data_date_bold_red
    @property
    def table_data_date_red_border(self):
        return self._table_data_date_border_red
    @property
    def table_data_date_red_border_bold(self):
        return self._table_data_date_border_bold_red
    @property
    def table_data_date_red_even(self):
        return self._table_data_date_even_red
    @property
    def table_data_date_red_even_bold(self):
        return self._table_data_date_even_bold_red
    @property
    def table_data_date_red_even_border(self):
        return self._table_data_date_even_border_red
    @property
    def table_data_date_red_even_border_bold(self):
        return self._table_data_date_even_border_bold_red

    @property
    def table_data_date_green(self):
        return self._table_data_date_green
    @property
    def table_data_date_green_bold(self):
        return self._table_data_date_bold_green
    @property
    def table_data_date_green_border(self):
        return self._table_data_date_border_green
    @property
    def table_data_date_green_border_bold(self):
        return self._table_data_date_border_bold_green
    @property
    def table_data_date_green_even(self):
        return self._table_data_date_even_green
    @property
    def table_data_date_green_even_bold(self):
        return self._table_data_date_even_bold_green
    @property
    def table_data_date_green_even_border(self):
        return self._table_data_date_even_border_green
    @property
    def table_data_date_green_even_border_bold(self):
        return self._table_data_date_even_border_bold_green

    @property
    def table_data_date_blue(self):
        return self._table_data_date_blue
    @property
    def table_data_date_blue_bold(self):
        return self._table_data_date_bold_blue
    @property
    def table_data_date_blue_border(self):
        return self._table_data_date_border_blue
    @property
    def table_data_date_blue_border_bold(self):
        return self._table_data_date_border_bold_blue
    @property
    def table_data_date_blue_even(self):
        return self._table_data_date_even_blue
    @property
    def table_data_date_blue_even_bold(self):
        return self._table_data_date_even_bold_blue
    @property
    def table_data_date_blue_even_border(self):
        return self._table_data_date_even_border_blue
    @property
    def table_data_date_blue_even_border_bold(self):
        return self._table_data_date_even_border_bold_blue

    @property
    def table_data_date_orange(self):
        return self._table_data_date_orange
    @property
    def table_data_date_orange_bold(self):
        return self._table_data_date_bold_orange
    @property
    def table_data_date_orange_border(self):
        return self._table_data_date_border_orange
    @property
    def table_data_date_orange_border_bold(self):
        return self._table_data_date_border_bold_orange
    @property
    def table_data_date_orange_even(self):
        return self._table_data_date_even_orange
    @property
    def table_data_date_orange_even_bold(self):
        return self._table_data_date_even_bold_orange
    @property
    def table_data_date_orange_even_border(self):
        return self._table_data_date_even_border_orange
    @property
    def table_data_date_orange_even_border_bold(self):
        return self._table_data_date_even_border_bold_orange

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