# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from odoo import exceptions, _
from datetime import datetime

class txtPopulaPayslip(models.Model):
    _name = 'txt.popular.payslip'

    name = fields.Char(string="Description", required=True, )
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 required=False, readonly=True, default=lambda self: self.env.user.company_id.id)
    payslip_run_id = fields.Many2one(comodel_name="hr.payslip.run", string="Lote de Nomina", required=True,
                                     domain="[('state', '=', 'review')]")
    report = fields.Binary(string="Reporte", readonly=True)
    report_name = fields.Char(string="Nombre de Reporte", readonly=True, )
    effective_date = fields.Date(string="Fecha Efectiva", required=True,
                                 help='Fecha Futura cuando  se aplicaran los pagos')
    email = fields.Char(string="Email", required=True, )
    sequence = fields.Char(string="Sequence", required=False, )
    lines_ids = fields.One2many(comodel_name="txt.popular.payslip.line", inverse_name="txt_popular_id", string="Lines", required=False, )
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency", required=True, )

    def create_report(self):

        for line in self.lines_ids:
            line.unlink()

        self.generate_report()


    @api.model
    def create(self, values):
        # Add code here

        values['sequence'] = self.env['ir.sequence'].next_by_code('bpd.payslip')


        return super(txtPopulaPayslip, self).create(values)

    def get_header(self):

        date = self.effective_date.split('-')[0] + self.effective_date.split('-')[1] + self.effective_date.split('-')[2]

        header = 'H' + self.company_id.vat.ljust(15, ' ') + 'FH'.ljust(35, ' ') \
                 + self.sequence + '01' + date + '0'.zfill(11) + '0'.zfill(13)

        total = self.get_total()

        hour = self.create_date.split(' ')[1].split(':')[0] + self.create_date.split(' ')[1].split(':')[1]

        header = header + total + '0'.zfill(15) + date + hour + self.email.ljust(40) + ' '.ljust(137)
        header =  header + '\r'

        return header

    def get_total(self):

        total = 0.00
        lines  = 0

        for payslip in self.payslip_run_id.slip_ids:
            for line in payslip.line_ids:
                if line.code == 'NET':
                    if payslip.employee_id.bank_account_id:

                        if payslip.employee_id.bank_account_id.currency_id == self.currency_id:
                            total = total + line.total
                            lines = lines + 1

        # decimals = str(total)[-2:].replace('.', '').zfill(2)

        str('%.2f' % total).replace('.', '')

        # return str(lines).zfill(11) + str(str(int(total)) + decimals).zfill(13)
        return str(lines).zfill(11) + str('%.2f' % total).replace('.', '').zfill(13)

    def get_lines(self):

        currency = '214'

        if self.currency_id.name == 'USD':
            currency = '840'

        lines = []

        count = 1

        for payslip in self.payslip_run_id.slip_ids:

            for line in payslip.line_ids:
                if line.code == 'NET':
                    cadena = 'N' + self.company_id.vat.ljust(15, ' ') + str(self.sequence).zfill(7)
                    if payslip.employee_id.bank_account_id and payslip.employee_id.identification_id:

                        if payslip.employee_id.bank_account_id.currency_id == self.currency_id:
                            # One line is:
                            # N = type of record
                            # Company's RNC
                            # Sequence of parent record


                            name = (payslip.employee_id.names.split(' ')[0] + ' ' + payslip.employee_id.first_lastname).upper()

                            cadena = cadena + str(count).zfill(7)
                            cadena = cadena + payslip.employee_id.bank_account_id.acc_number.replace('-','').ljust(20)
                            cadena = cadena + '1' + currency + '10101070' + '8' + '22'
                            cadena = cadena + str('%.2f' % line.total).replace('.', '').zfill(13) + 'CE'
                            # decimals = str(line.total)[-2:].replace('.', '').zfill(2)
                            # cadena = cadena + str(str(int(line.total)) + decimals).zfill(13)+ 'CE'
                            cadena = cadena + payslip.employee_id.identification_id.replace('-', '').ljust(15)
                            cadena = cadena + name[0:35].ljust(35)
                            cadena = cadena + ' '.ljust(12)
                            cadena = cadena + 'PAGO NOMINA AUTOMATICA'.ljust(40)
                            cadena = cadena + ' '.ljust(4)
                            cadena = cadena + '1' + payslip.employee_id.work_email[0:40].ljust(40) or ' '.ljust(40)
                            cadena = cadena + ' '.ljust(12) + '00'
                            cadena = cadena + ' '.ljust(79)

                            lines.append(cadena + '\r')

                            self.env['txt.popular.payslip.line'].create(
                                {
                                    'no_line': count,
                                    'account_bank':payslip.employee_id.bank_account_id.acc_number,
                                    'amount': line.total,
                                    'identification_id': payslip.employee_id.identification_id,
                                    'name': payslip.employee_id.name,
                                    'email_employee': payslip.employee_id.work_email,
                                    'txt_popular_id': self.id,
                                }
                            )

                            count = count + 1
        return lines


    def generate_report(self):

        name_file = '/tmp/bpd_txt.txt'

        file_txt = open('/tmp/bpd_txt.txt', "w")
        lines = self.sudo().get_lines()
        header_txt = self.sudo().get_header()

        file_txt.write(header_txt + '\n')
        for l in lines:
            file_txt.write(l + '\n')

        file_txt.close()
        file_txt = open('/tmp/bpd_txt.txt', 'rb')

        self.report = base64.b64encode(file_txt.read())
        file_txt.close()
        self.report_name = self.get_file_name()

    def get_file_name(self):

        name = 'PE'
        name = name + '076490' + '01'

        date = self.effective_date.split('-')[1] + self.effective_date.split('-')[2]

        name = name + date + self.sequence + 'E.txt'

        return name


class txtPopulaPayslipLine(models.Model):
    _name = 'txt.popular.payslip.line'

    no_line = fields.Integer(string="Number of line", required=False, )
    account_bank = fields.Char(string="Account bank", required=False, )
    amount = fields.Float(string="amount",  required=False, )
    identification_id = fields.Char(string="Identification Document", required=False, )
    name = fields.Char(string="Name of Employee", required=False, )
    email_employee = fields.Char(string="E-mail Employee", required=False, )
    txt_popular_id = fields.Many2one(comodel_name="txt.popular.payslip", string="", required=False, )



