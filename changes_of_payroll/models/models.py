# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import base64
import xlwt
from io import BytesIO
from xlrd import open_workbook
import xlrd
from odoo import exceptions, _


class ChangesPayroll(models.Model):
    _name = 'changes.payroll'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string="Description", required=True, )
    date = fields.Date(string="Date", required=False, default=datetime.today())
    file_changes = fields.Binary(string="File of Changes",  )
    template_changes = fields.Binary(string="Template of Changes",  )
    name_file = fields.Char(string="Name of File", required=False, )
    payslip_run_id = fields.Many2one(comodel_name="hr.payslip.run", string="Payslip", required=False, )
    lines_ids = fields.One2many(comodel_name="changes.payroll.line", inverse_name="changes_payroll_id", string="Lines", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('validated', 'Validated'),
                                                        ('review', 'Reviewed'),
                                                        ('close', 'Close'), ], required=False,
                             default='draft',track_visibility='onchange' )


    @api.multi
    def unlink(self):
        if self.state != 'draft':
            raise exceptions.UserError(_('This form must have to be in draft for deletion'))
        else:
            return super(ChangesPayroll, self).unlink()

    @api.multi
    def generate_template(self):
        filename = 'template_changes.xls'

        workbook = xlwt.Workbook()

        worksheet = workbook.add_sheet('Template of Changes')

        header = ['Change', 'Name of Change', 'Code of Employee', 'Name of Employe', 'Amount',
                  'Apply on', 'Date']

        column = 0

        for h in header:

            worksheet.write(0, column, h)

            column = column + 1

        row = 1
        types_changes = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id)])

        for t in types_changes:
            worksheet.write(row, 0, t.code)
            worksheet.write(row, 1, t.name)
            row = row + 1

        stream = BytesIO()

        workbook.save(stream)

        self.template_changes = base64.encodestring(stream.getvalue())
        self.name_file = 'template_changes.xls'
        stream.close()

    def genetare_lines(self):

        if self.lines_ids:
            ids = []
            for l in self.lines_ids:
                l.unlink()

        file_data = base64.decodestring(self.file_changes)
        wb = open_workbook(file_contents=file_data)

        data = []

        row = 1
        column = 0

        sheet = wb.sheet_by_index(0)

        tempDate = datetime(1900, 1, 1)

        # datetime.fromordinal(int(


        while True:
            try:
                code = sheet.cell_value(row, column)
                code_employee = sheet.cell_value(row, column + 2)

                code = self.get_type_change(code)
                code_employee = self.get_employe(code_employee)
                contract = self.get_contract(code_employee)

                # # raise exceptions.UserError(_(sheet.cell_value(row, column + 6)))
                cellda1 = sheet.cell_value(row, column + 6)
                # cellda2 = sheet.cell_value(row, column + 9)
                date = datetime(*xlrd.xldate_as_tuple(cellda1, wb.datemode))
                # date_to = datetime(*xlrd.xldate_as_tuple(cellda2, wb.datemode))

                # date_from = (tempDate + timedelta(int(sheet.cell_value(row, column + 6))))
                # raise exceptions.UserError(_(date_test))
                # date_to = (tempDate + timedelta(int(sheet.cell_value(row, column + 7))))

                data.append(
                    {
                        'change': code,
                        'employee': code_employee,
                        'amount': sheet.cell_value(row, column + 4),
                        'apply_on': str(int(sheet.cell_value(row, column + 5))),
                        'date': date,
                        'contract': contract
                    }
                )

                row = row + 1
            except IndexError:
                break

        self.write_lines(data)

    def write_lines(self, data):

        for line in data:

            self.env['changes.payroll.line'].create(
                {
                    'type_change_id.id': line['change'],
                    'employee_id.id': line['employee'],
                    'amount': line['amount'],
                    'apply_on': line['apply_on'],
                    'changes_payroll_id': self.id,
                    'contract_id': line['contract'],
                    'date': line['date']
                }
            )

    def get_contract(self,ID):
        return self.env['hr.contract'].search([['employee_id', '=', ID]])[0].id

    def get_employe(self, code):

        return self.env['hr.employee'].search([['code','=',code]])[0].id

    def get_type_change(self,code):

        return self.env['changes.payroll.type'].search([['code','=',code]])[0].id

    def _track_subtype(self, init_values):
        # init_values contains the modified fields' values before the changes
        # the applied values can be accessed on the record as they are already
        # in cache
        self.ensure_one()
        if 'state' in init_values and self.state == 'approved':
            return 'changes_of_payroll.mt_state_change'  # Full external id
        elif 'state' in init_values and self.state == 'close':
            return 'changes_of_payroll.mt_state_change_close'  # Full external id
        return super(ChangesPayroll, self)._track_subtype(init_values)

    def review_this(self):

        self.write({'state': 'review'})


    def approve_this(self):

        self.write({'state': 'validated'})

        if self.lines_ids:
            for l in self.env['changes.payroll.line'].search([['changes_payroll_id', '=', self.id]]):
                l['state'] = 'validated'

    def close_this(self):

        self.write({'state': 'close'})

        if self.lines_ids:
            for l in self.env['changes.payroll.line'].search([['changes_payroll_id', '=', self.id]]):
                if l['type_change_id'].type_of == 'wage':
                    contract = l['employee_id'].contract_id.id
                    rec = self.env['hr.contract.salary'].create({
                        'date': l['date'],
                        'amount': l['amount'],
                        'concept': 'wage',
                        'contract_id': contract
                    })
                    rec.contract_id.onchange_wage()
                elif l['type_change_id'].type_of == 'bonus':
                    contract = l['employee_id'].contract_id.id
                    rec = self.env['hr.contract.salary'].create({
                        'date': l['date'],
                        'amount': l['amount'],
                        'concept': 'bonus',
                        'contract_id': contract
                    })
                    rec.contract_id.onchange_wage()
                elif l['type_change_id'].type_of == 'termination':
                    l['employee_id'].contract_id.state = 'cancel'
                    l['employee_id'].active = False



                l['state'] = 'close'

    def draft_this(self):
        self.write({'state': 'draft'})
        if self.lines_ids:
            for l in self.env['changes.payroll.line'].search([['changes_payroll_id', '=', self.id]]):
                l['state'] = 'draft'

    def get_change(self,code, date, apply_on, employee):

        date_slt = date.split('-')
        date_from = date_slt[0] + '-' + date_slt[1] + '-' + '-' + '01'

        change = self.env['changes.payroll.line'].search([('employee_id', '=', employee),
                                                          ('date', '<=', date),
                                                          ('date', '>=', date_from),
                                                          ('code', '=', code),
                                                          ('apply_on', '=', apply_on),
                                                          '|',
                                                          ('state', '=', 'validated'), ('state', '=', 'close')])

        # change = self.env['changes.payroll.line'].search([('employee_id', '=', employee),
        #                                                   ('code', '=', code),
        #                                                   ('apply_on', '=', apply_on),
        #                                                   ('state', '=', 'close')])
        #

        plus = 0.0

        for c in change:
            plus = plus + c.amount

        return plus


class LinesChangesPayroll(models.Model):
    _name = 'changes.payroll.line'
    _order = "date desc"

    @api.model
    def create(self, values):
        # Add code here

        if 'type_change_id.id' in values:
            values['type_change_id'] = values['type_change_id.id']

        if 'employee_id.id' in values:
            values['employee_id'] = values['employee_id.id']

        contract = self.env['hr.contract'].search([('employee_id', '=', values['employee_id'])])[0]
        values['contract_id'] = contract.id

        return super(LinesChangesPayroll, self).create(values)


    type_change_id = fields.Many2one(comodel_name="changes.payroll.type", string="Type of change", required=False, )
    code = fields.Char(string="Code of change", required=False, related="type_change_id.code")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False,
                                  )
    code_employee = fields.Char(string="Code of employee", required=False, related="employee_id.code")
    name = fields.Char(string="Name", required=False, related="type_change_id.name")
    amount = fields.Float(string="Amount",  required=False, )
    date = fields.Date(string="Date", required=False)
    apply_on = fields.Selection(string="Apply on", selection=[('1', 'First Period'),
                                                                ('2', 'Second Period'),
                                                                ('3', 'Month'), ],
                                required=False, )
    changes_payroll_id = fields.Many2one(comodel_name="changes.payroll", string="Main", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State",
                             selection=[('draft', 'Draft'), ('validated', 'Validated'), ('close', 'Close'), ],
                             required=False,
                             default='draft')
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", required=False, )

class TypesChanges(models.Model):
    _name = 'changes.payroll.type'

    name = fields.Char(string="Change", required=True, )
    code = fields.Char(string="Code", required=True, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    type_of = fields.Selection(string="Type", selection=[('rule', 'Salary Rule'),
                                                         ('wage', 'Wage'),
                                                         ('bonus', 'Bonus'),
                                                         ('contract', 'Contract'),
                                                         ('termination', 'Termination'),
                                                         ],
                             required=False, default='rule')

class HRPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    changes_id = fields.Many2one(comodel_name="changes.payroll", string="Changes", required=False, )

class HRContract(models.Model):
    _inherit = 'hr.contract'

    changes_ids = fields.One2many(comodel_name="changes.payroll.line", inverse_name="contract_id",
                                  string="Changes", required=False, domain=[('state', '=', 'close'),
                                                                            '|',
                                                                            ('type_change_id.type_of', '=', 'contract'),
                                                                            ('type_change_id.type_of', '=', 'termination')])

    wage = fields.Monetary('Wage', digits=(16, 2), required=False, track_visibility="onchange",
                           help="Employee's monthly gross wage.")
