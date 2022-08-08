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
    _order = 'date'


    name = fields.Char(string="Payroll Run", required=False, )
    date = fields.Date(string="Created on", required=False, default=datetime.today())
    file_changes = fields.Binary(string="File of Changes",  )
    template_changes = fields.Binary(string="Template of Changes",  )
    name_file = fields.Char(string="Name of File", required=False, )
    payslip_run_id = fields.Many2one(comodel_name="hr.payslip.run", string="Payslip", required=False, )
    lines_ids = fields.One2many(comodel_name="changes.payroll.line", inverse_name="changes_payroll_id", string="Lines", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State", selection=[('draft', 'Submitted'), ('validated', 'Processed'),
                                                        ('close', 'Close'), ], required=False,
                             default='draft', track_visibility='onchange' )
    is_generated = fields.Boolean(string="Generate Lines",  )
    change_payroll_sequence = fields.Char(string='Consolidate Reference', required=True, copy=False, readonly=True,)
    year = fields.Selection(string='Year',
                            selection=[(year, str(year)) for year in range(2019, (datetime.now().year) + 2)],
                            required=False,  default=lambda self: self._get_default_year())
    month = fields.Selection(string='Month',
                             selection=[('1', 'Jan'),
                                        ('2', 'Feb'),
                                        ('3', 'Mar'),
                                        ('4', 'Apr'),
                                        ('5', 'May'),
                                        ('6', 'Jun'),
                                        ('7', 'Jul'),
                                        ('8', 'Aug'),
                                        ('9', 'Sep'),
                                        ('10', 'Oct'),
                                        ('11', 'Nov'),
                                        ('12', 'Dec'),
                                        ],
                             required=False, default=lambda self: self._get_default_month())

    def _get_default_month(self):
        return str(datetime.now().month)

    def _get_default_year(self):
        return datetime.now().year

    @api.model
    def create(self, vals):
        # vals['name'] = self.env['ir.sequence'].next_by_code('changes.payroll') or '/'
        month_dict = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
                      7: 'July', 8: 'August',
                      9: 'September', 10: 'October', 11: 'November', 12: 'December'}

        company_code = self.env.user.company_id.business_unit_code
        year = str(datetime.now().year)

        prefix = str(company_code) + '-' + 'One-Time-Changes-' + year + '-' + str(month_dict[datetime.now().month])

        payroll = self.search([('name', '=like', prefix + '%')])

        seq = ''

        if payroll:
            seq = prefix + '-' + str(len(payroll) + 1)
        else:
            seq = prefix
        vals['name'] = seq
        vals['change_payroll_sequence'] = seq

        return super(ChangesPayroll, self).create(vals)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(ChangesPayroll, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id',  ]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res

    def delete_lines_load(self):

        lines = self.env['changes.payroll.line'].search(
            [('type_line', '!=', 'onetime'), ('changes_payroll_id', '=', self.id)]
        )

        lines.unlink()


    def create_changes_by_employee(self):

        self.delete_lines_load()

        dict_month = {
            1: '31', 2: '28', 3: '31', 4: '30', 5: '31', 6: '30', 7: '31', 8: '31', 9: '30', 10: '31', 11: '30',
            12: '31'
        }

        date = self.date.split('-')
        date_from = date[0] + '-' + date[1] + '-' + '01'
        date_to = date[0] + '-' + date[1] + '-' + dict_month[int(date[1])]

        requests = self.env['change.payroll.request'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
        ])

        for request in requests:

            if request.change_amount_wire > 0 or request.balance_wire\
                    or request.change_dep1_amount > 0 or request.balance_dep1\
                    or request.change_dep2_amount > 0 or request.balance_dep2\
                    or request.change_cash_amount > 0 or request.balance_cash:

                concept = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                               ('is_payment_distribution', '=', True)], limit=1)

                self.env['changes.payroll.line'].create(
                    {
                        'type_change_id.id': concept.id,
                        'employee_id.id': request.employee_id.id,
                        'amount': 0.0,
                        'apply_on': '3',
                        'changes_payroll_id': self.id,
                        'contract_id': request.employee_id.contract_id.id,
                        'date': request.date,
                        'request_id': request.id
                    }
                )

            # change_pension_amount
            # pension_amount_percent

            if request.change_pension_amount:
                concept_pension = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                                   ('type_of', '=', 'pension')], limit=1)

                if not request.pension_amount_percent:
                    self.env['changes.payroll.line'].create(
                        {
                            'type_change_id.id': concept_pension.id,
                            'employee_id.id': request.employee_id.id,
                            'amount': change_pension_amount,
                            'apply_on': '3',
                            'changes_payroll_id': self.id,
                            'contract_id': request.employee_id.contract_id.id,
                            'date': request.date,
                            'request_id': request.id,
                            'is_pension': 'yes'
                        }
                    )
                else:
                    self.env['changes.payroll.line'].create(
                        {
                            'type_change_id.id': concept_pension.id,
                            'employee_id.id': request.employee_id.id,
                            'percent': change_pension_amount,
                            'apply_on': '3',
                            'changes_payroll_id': self.id,
                            'contract_id': request.employee_id.contract_id.id,
                            'date': request.date,
                            'request_id': request.id,
                            'is_pension': 'yes'
                        }
                    )


            for line in request.lines_ids:
                if request.state == 'done':

                    self.env['changes.payroll.line'].create(
                        {
                            'type_change_id.id': line.type_change_id.id,
                            'employee_id.id': line.employee_id.id,
                            'amount': line.amount,
                            'apply_on': '3',
                            'changes_payroll_id': self.id,
                            'contract_id': line.contract_id.id,
                            'date': line.date,
                            'file_action': line.file_action,
                            'name_file': line.name_file,
                            'type_line': 'request',
                        }
                    )

        personal_actions = self.env['changes.payroll.fixed.line'].search([
            ('company_id', '=', self.company_id.id),
            ('date_from', '<=', date_to),
            ('date_from', '>=', date_from),
            ('state', '=', 'validated')
        ])

        for action in personal_actions:

            self.env['changes.payroll.line'].create(
                {
                    'type_change_id.id': action.type_change_id.id,
                    'employee_id.id': action.employee_id.id,
                    'amount': action.amount,
                    'apply_on': action.apply_on,
                    'changes_payroll_id': self.id,
                    'contract_id': action.contract_id.id,
                    'date': action.date_from,
                    'percent': action.percent,
                    'type_line': 'personal'
                }
            )

        hr_salary_history = self.env['hr.contract.salary'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '<=', date_to),
            ('date', '>=', date_from),
            ('state', '=', 'validate')

        ])

        for salary in hr_salary_history:
            concept_s = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                               ('type_of', '=', 'wage')], limit=1)

            self.env['changes.payroll.line'].create(
                {
                    'type_change_id.id': concept_s.id,
                    'employee_id.id': salary.employee_id.id,
                    'amount': salary.amount,
                    'apply_on': '3',
                    'changes_payroll_id': self.id,
                    'contract_id': salary.contract_id.id,
                    'date': salary.date,
                    'type_line': 'wage'
                }
            )

    @api.multi
    def write(self, values):
        # Add code here

        if 'date' in values:
            if self.lines_ids:
                for line in self.lines_ids:
                    line.date = values['date']


        return super(ChangesPayroll, self).write(values)


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

        header = ['Change', 'Name of Change', 'Code of Employee', 'Name of Employee', 'Amount',
                  'Apply on']

        column = 0

        for h in header:

            worksheet.write(0, column, h)

            column = column + 1

        row = 1
        types_changes = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                                 ('type_of', '=', 'rule')])

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
        if not self.file_changes:
            raise exceptions.UserError(_("This form don't have file for generate line"))

        if self.lines_ids:

            lines = self.env['changes.payroll.line'].search(
                [('type_line', '=', 'onetime'), ('changes_payroll_id', '=', self.id)]
            )

            lines.unlink()

            ids = []
            # for l in self.lines_ids:
            #     lines.unlink()

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
                # cellda1 = sheet.cell_value(row, column + 6)
                # # cellda2 = sheet.cell_value(row, column + 9)
                # date = datetime(*xlrd.xldate_as_tuple(cellda1, wb.datemode))
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
                        'date': self.date,
                        'contract': contract
                    }
                )

                row = row + 1
            except IndexError:
                break

        self.write_lines(data)

        self.is_generated = True

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

    def approve_this(self):

        self.write({'state': 'validated'})

        if self.lines_ids:
            for l in self.env['changes.payroll.line'].search([['changes_payroll_id', '=', self.id]]):
                l['state'] = 'validated'

    def close_this(self):

        self.write({'state': 'close'})

        if self.lines_ids:
            for l in self.env['changes.payroll.line'].search([['changes_payroll_id', '=', self.id]]):
                if l['amount'] < 0:
                    message = 'You can not put an amount in negative\nEmployee: %s' % (l['employee_id'].name)

                    raise exceptions.UserError(_(message))
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

                elif l['type_change_id'].type_of == 'percentage':

                    if l['amount'] <= 0:
                        message = 'You can not put an percentage in negative or zero (0)\nEmployee: %s' % (l['employee_id'].name)

                        raise exceptions.UserError(_(message))

                    if l['amount'] > 25.00:
                        u = "{0:.0f}%".format(25)
                        message = 'You can not put an percentage greater that %s\nEmployee: %s' % (u, l['employee_id'].name)

                        raise exceptions.UserError(_(message))


                    percent = (l['amount'] / 100) + 1

                    contract = l['employee_id'].contract_id.id
                    rec = self.env['hr.contract.salary'].create({
                        'date': l['date'],
                        'amount': l['employee_id'].contract_id.wage * percent,
                        'concept': 'wage',
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

        if 'changes_payroll_id' in values:
            change = self.env['changes.payroll'].search(
                [('id', '=', values['changes_payroll_id'])]
            )[0]

            values['date'] = change.date

        return super(LinesChangesPayroll, self).create(values)


    type_change_id = fields.Many2one(comodel_name="changes.payroll.type", string="Type of change",
                                     required=False, domain=['|', ('type_of', '=', 'rule'),
                                                             ('type_of', '=', 'percentage')])
    code = fields.Char(string="Code of change", required=False, related="type_change_id.code")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False,
                                  )
    code_employee = fields.Char(string="Code of employee", required=False, related="employee_id.code")
    name = fields.Char(string="Name", required=False, related="type_change_id.name")
    amount = fields.Float(string="Amount",  required=False, )
    is_pension = fields.Selection(string="Is Pension?", selection=[('no', 'No'), ('yes', 'Yes')])
    pension_percentage = fields.Float(string="Pension Amount", required=False)
    pension_percentage_calc = fields.Char(string="Percentage", compute='_percentage_calculation')
    date = fields.Date(string="Date", required=False, default=datetime.today())
    apply_on = fields.Selection(string="Entered by", selection=[('1', 'First Period'),
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
    file_action = fields.Binary(string="File", )
    request_id = fields.Many2one(comodel_name="change.payroll.request", string="Employee Request", required=False, )
    name_file = fields.Char(string="File name", required=False, )
    type_line = fields.Selection(string="Type Line", selection=[('request', 'Request Employee'),
                                                                ('wage', 'Wage'),
                                                                ('personal', 'Personal Action'),
                                                                ('onetime', 'One-Time'),
                                                                ], required=False, default='onetime')
    percent = fields.Float(
        string='Percent',
        required=False)

    @api.one
    def _percentage_calculation(self):
        if self.pension_percentage > 0:
            self.pension_percentage_calc = str(int(self.pension_percentage / 100)) + "%"


class TypesChanges(models.Model):
    _name = 'changes.payroll.type'

    name = fields.Char(string="Change", required=True, )
    code = fields.Char(string="Code", required=True, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    type_of = fields.Selection(string="Type", selection=[('rule', 'Change'),
                                                         ('wage', 'Wage'),
                                                         ('percentage', 'Wage Percentage'),
                                                         ('contract', 'Personal Action'),
                                                         ('termination', 'Termination'),
                                                         ('pension', 'Pension'),
                                                         ('employee', 'Employee'),
                                                         ('pay_distrib', 'Payment Distribution'),
                                                         ('position', 'Contract'),

                                                         ],
                             required=False, default='rule')
    to_employee = fields.Boolean(string="To Employee",  )
    is_payment_distribution = fields.Boolean(string="For Payment Distribution",  )
    allo_ded = fields.Selection(string="Allowance/Deduction",
                                selection=[('allowance', 'Allowance'), ('deduction', 'Deduction'), ],
                                required=False, )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(TypesChanges, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id', 'name', ]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res

class Payslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(Payslip, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id', 'name', ]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res


class HRPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    changes_id = fields.Many2one(comodel_name="changes.payroll", string="Changes", required=False, )

    changes_ids = fields.Many2many(comodel_name="changes.payroll", relation="rel_changes_hr_payslip_run",
                                   column1="payslip_run_id",
                                   column2="changes_id", string="Changes", )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(HRPayslipRun, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id', 'name', ]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res

    @api.multi
    def write(self, values):
        # Add code here
        ID = super(HRPayslipRun, self).write(values)

        if not self.changes_ids:
            changes = self.env['changes.payroll'].search([('date', '>=', self.date_start),
                                                          ('date', '<=', self.date_end),
                                                          ('state', '!=', 'close'),
                                                          ])
            for change in changes:
                self.changes_ids = [(4, changes.id, _)]
                change.payslip_run_id = self.id

        return ID

    @api.model
    def create(self, values):
        # Add code here
        ID = super(HRPayslipRun, self).create(values)

        changes = self.env['changes.payroll'].search([('date', '>=', ID.date_start),
                                                      ('date', '<=', ID.date_end),
                                                      ('state', '!=', 'close'),
                                                      ])


        for change in changes:
            ID.changes_ids = [(4, change.id, _)]
            change.payslip_run_id = ID.id


        return ID

    @api.multi
    def ConfirmPayslips(self):
        self.ensure_one()

        for change in self.changes_ids:
            if change.state != 'close':
                raise exceptions.UserError(_('You Has Any Changes Of The Month Without Close'))

        super(HRPayslipRun, self).ConfirmPayslips()

class HRContract(models.Model):
    _inherit = 'hr.contract'

    changes_ids = fields.One2many(comodel_name="changes.payroll.line", inverse_name="contract_id",
                                  string="Changes", required=False, domain=[('state', '=', 'close')])

    wage = fields.Monetary('Wage', digits=(16, 2), required=False, track_visibility="onchange",
                           help="Employee's monthly gross wage.")
    personal_actions_ids = fields.One2many(comodel_name="changes.payroll.fixed.line",
                                           inverse_name="contract_id", string="Personal Actions", required=False, )

class LinesChangesFixedPayroll(models.Model):
    _name = 'changes.payroll.fixed.line'
    _order = "date_from desc"

    description_pension_id = fields.Many2one(comodel_name="description.pension", string="Description", required=False, )
    type_action = fields.Selection(string="Type", selection=[('contract', 'Personal Action'),
                                                         ('termination', 'Termination'),
                                                         ('pension', 'Pension'),
                                                   ], required=False,
                                   related="type_change_id.type_of")
    type_change_id = fields.Many2one(comodel_name="changes.payroll.type", string="Type of change",
                                     required=True, domain=['|', ('type_of', '=', 'contract'),
                                                            ('type_of', '=', 'pension')])
    amount = fields.Float(string="Amount",  required=False, )
    is_pension = fields.Selection(string="Is Pension?", selection=[('no', 'No'), ('yes', 'Yes')])
    pension_percentage = fields.Float(string="Pension Amount", required=False)
    pension_percentage_calc = fields.Char(string="Percentage", compute='_percentage_calculation')
    frequency = fields.Selection(string="Frequency", selection=[('fixed', 'Fixed'), ('variable', 'Variable'), ],
                                 required=True, default='fixed')
    date_from = fields.Date(string="Date From", required=True, default=datetime.today())
    date_to = fields.Date(string="Date To", required=False)
    apply_on = fields.Selection(string="Apply on", selection=[('1', 'First Period'),
                                                                ('2', 'Second Period'),
                                                                ('3', 'Month'), ],
                                required=True, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State",
                             selection=[('draft', 'Draft'), ('validated', 'Validated'), ],
                             required=False,
                             default='draft')
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", required=False, )
    currency_id = fields.Many2one(string="Currency", related='contract_id.currency_id', readonly=False)
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )
    allo_ded = fields.Selection(string="Allowance/Deduction",
                                selection=[('allowance', 'Allowance'), ('deduction', 'Deduction'), ],
                                required=False, related="type_change_id.allo_ded")
    attachment_line = fields.Binary(string="Attachment", )
    attachment_line_name = fields.Char(string="Attachment Name", required=False, )
    percent = fields.Float(
        string='Percent',
        required=False)

    @api.constrains('percent')
    def _check_percent_amount(self):
        for record in self:
            if record.percent > 100.00:
                raise ValidationError("Percent must be less than or equal to 100.00")
        # all records passed the test, don't return anything


    @api.one
    def _percentage_calculation(self):
        if self.pension_percentage > 0:
            self.pension_percentage_calc = str(int(self.pension_percentage / 100)) + "%"

    @api.model
    def create(self, values):
        # Add code here

        ID = super(LinesChangesFixedPayroll, self).create(values)

        ID.contract_id = ID.employee_id.contract_id

        if ID.amount == 0.00 and ID.percent == 0.00:
            raise exceptions.UserError(_("You must be fill amount or percent."))

        return ID

    def unlink(self):

        if self.state == 'validated':
            raise exceptions.UserError(_("You can't delete this record if It is validated"))

        return super(LinesChangesFixedPayroll, self).unlink()

    def draft_this(self):

        self.state = 'draft'
        if self.type_change_id.type_of == 'wage':
            salary = self.env['hr.contract.salary'].search(
                [('change_id', '=', self.id)]
            )

            for sal in salary:
                sal.unlink()

            self.contract_id.onchange_wage()

        if self.type_change_id.type_of == 'termination':
            self.contract_id.state = 'open'

        allo_ded = {'allowance': 'Allowance', 'deduction': 'Deduction'}

        message = "The %s %s Was Undone" % (allo_ded[self.allo_ded], self.type_change_id.name)

        self.employee_id.message_post(message, subtype='mail.mt_note')

    def validate_this(self):

        self.contract_id = self.employee_id.contract_id

        if self.type_change_id.type_of == 'wage':
            rec = self.env['hr.contract.salary'].create({
                'date': self.date_from,
                'amount': self.amount,
                'pension_percentage': self.pension_percentage,
                'pension_percentage_calc': self.pension_percentage_calc,
                'concept': 'wage',
                'contract_id': self.contract_id.id,
                'change_id': self.id
            })
            rec.contract_id.onchange_wage()
            self.employee_id.wage = self.amount

        elif self.type_change_id.type_of == 'termination':
            self.contract_id.state = 'cancel'
            self.contract_id.employee_id.active = False
        elif self.type_change_id.type_of == 'pension':
            self.employee_id.pension_amount = self.amount
            self.employee_id.description_pension_id = self.description_pension_id

        self.state = 'validated'

        allo_ded = {'allowance': 'Allowance', 'deduction': 'Deduction'}

        message = "The %s %s Was Approved" % (allo_ded[self.allo_ded], self.type_change_id.name)

        self.employee_id.message_post(message, subtype='mail.mt_note')

    def get_amount(self, code, date_from, date_to, period, contract):

        total = 0.0

        change = self.env['changes.payroll.type'].search(
            [('code', '=', code), ('company_id', '=', self.env.user.company_id.id)]
        )[0]

        lines = self.env['changes.payroll.fixed.line'].search(
            [('type_change_id', '=', change.id),
             ('contract_id', '=', contract),
             ('state', '=', 'validated')
             ]
        )

        for line in lines:

            if line.apply_on == period:

                if line.date_to:
                    if not line.date_to < date_to:
                        total = total + line.amount
                else:

                    if date_to >= line.date_from:

                        total = total + line.amount

        return total

class HRContractSalary(models.Model):
    _inherit = 'hr.contract.salary'

    change_id = fields.Many2one(comodel_name="changes.payroll.fixed.line",
                                string="Change Line", required=False, )


class PayrollRequest(models.Model):
    _name = 'change.payroll.request'
    _description = 'Payroll Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string="Name", required=False, )
    date = fields.Date(string="Date", required=False, default=datetime.today())

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )
    user_id = fields.Many2one(comodel_name="res.users", string="User", required=False,
                              default=lambda self: self.env.user.id)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 required=False, readonly=True, default=lambda self: self.env.user.company_id.id)

    lines_ids = fields.One2many(comodel_name="changes.employee.report",
                                    inverse_name="payroll_request_id",
                                    string="Requests", required=False, )
    request_type = fields.Char(string="Request Type", related="lines_ids.name")
    request_date = fields.Date(string="Process on", related="lines_ids.date")
    state = fields.Selection(string="State", selection=[('draft', 'Submitted'), ('validate', 'Confirmed'), ('done', 'Processed'), ],
                             required=False, default='draft')
    distribution_ids = fields.One2many(comodel_name="distribution.payment.request", inverse_name="request_id", string="Payment Distribution", required=False, )

    change_amount_wire = fields.Float(string="Amount Wire", required=False, )
    balance_wire = fields.Boolean(string="Balance Wire", )
    frequency_wire = fields.Selection(string="Frequency", selection=[('once', 'Once-time'), ('permanent', 'Permanent'), ], required=False, )

    change_dep1_amount = fields.Float(string="Amount Deposit 1", required=False, )
    balance_dep1 = fields.Boolean(string="Balance Deposit 1", )
    frequency_dep1 = fields.Selection(string="Frequency", selection=[('once', 'Once-time'), ('permanent', 'Permanent'), ],
                                 required=False, )

    change_dep2_amount = fields.Float(string="Amount Deposit 2", required=False, )
    balance_dep2 = fields.Boolean(string="Balance Deposit 2", )
    frequency_dep2 = fields.Selection(string="Frequency", selection=[('once', 'Once-time'), ('permanent', 'Permanent'), ],
                                 required=False, )

    change_cash_amount = fields.Float(string="Amount Cash", required=False, )
    balance_cash = fields.Boolean(string="Balance Cash",  )
    frequency_cash = fields.Selection(string="Frequency", selection=[('once', 'Once-time'), ('permanent', 'Permanent'), ],
                                 required=False, )

    change_pension_amount = fields.Float(string="Amount Pension", required=False, )
    pension_amount_percent = fields.Boolean(
        string='Pension Amount Percent',
        required=False)

    @api.onchange('date')
    def onchange_method_date(self):
        for line in self.lines_ids:
            line.date = self.date

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(PayrollRequest, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id', 'name',]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res

    @api.onchange('balance_wire')
    def onchange_balance_wire(self):
        self.balance_dep2 = False
        self.balance_cash = False
        self.balance_dep1 = False

    @api.onchange('balance_dep1')
    def onchange_balance_dep1(self):
        self.balance_dep2 = False
        self.balance_cash = False
        self.balance_wire = False

    @api.onchange('balance_dep2')
    def onchange_balance_dep2(self):
        self.balance_dep1 = False
        self.balance_cash = False
        self.balance_wire = False

    @api.onchange('balance_cash')
    def onchange_balance_cash(self):
        self.cash_amount = 0.0
        self.balance_dep1 = False
        self.balance_dep2 = False
        self.balance_wire = False



    def unlink(self):

        if self.state == 'done':
            raise exceptions.UserError(_('You cannot delete if the document is done'))

        return super(PayrollRequest, self).unlink()

    @api.model
    def create(self, values):
        # Add code here

        seq = self.env['ir.sequence'].next_by_code('employee.request')
        employee = self.env['hr.employee'].search([('id', '=', values['employee_id'])], limit=1)

        values['name'] = employee.code + ' ' + employee.name + ' ' + seq

        ID = super(PayrollRequest, self).create(values)

        return ID

    def approve_this(self):
        self.state = 'validate'

    def do_this(self):

        if self.change_amount_wire > 0 or self.balance_wire:
            if self.balance_wire:
                self.employee_id.balance_to = 'wire'

            else:
                self.employee_id.amount_wire = self.change_amount_wire

        if self.change_dep1_amount > 0 or self.balance_dep1:

            if self.balance_dep1:

                self.employee_id.balance_to = 'dep1'

            else:

                self.employee_id.dep1_amount = self.change_dep1_amount


        if self.change_dep2_amount > 0 or self.balance_dep2:

            if self.balance_dep2:

                self.employee_id.balance_to = 'dep2'

            else:
                self.employee_id.dep2_amount = self.change_dep2_amount

        if self.change_cash_amount > 0 or self.balance_cash:

            if self.balance_cash:
                self.employee_id.balance_to = 'cash'

            else:
                self.employee_id.cash_amount = self.change_cash_amount

        if self.change_pension_amount > 0.0:
            concept_pension = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                                       ('type_of', '=', 'pension')], limit=1)

            personal_action = self.env['changes.payroll.fixed.line']\
                .search([('company_id', '=', self.company_id.id),
                         ('type_action', '=', 'pension')], limit=1)

            if self.pension_amount_percent:
                self.env['changes.payroll.fixed.line'].create({
                    'type_change_id': concept_pension.id,
                    'apply_on': '3',
                    'date_from': self.date,
                    'state': 'draft',
                    'percent': self.change_pension_amount,
                    'employee_id': self.employee_id.id
                })
            else:
                self.env['changes.payroll.fixed.line'].create({
                    'type_change_id': concept_pension.id,
                    'apply_on': '3',
                    'date_from': self.date,
                    'state': 'draft',
                    'amount': self.change_pension_amount,
                    'employee_id': self.employee_id.id
                })


        self.state = 'done'

    def draft_this(self):

        self.state = 'draft'


    def _track_subtype(self, init_values):
        # init_values contains the modified fields' values before the changes
        # the applied values can be accessed on the record as they are already
        # in cache
        self.ensure_one()
        if 'state' in init_values and self.state == 'done':
            return 'changes_of_payroll.mt_state_change_employee_request_done'  # Full external id

        return super(PayrollRequest, self)._track_subtype(init_values)

    @api.model
    def default_get(self, field_list):
        result = super(PayrollRequest, self).default_get(field_list)
        # if 'employee_id' in field_list and result.get('user_id'):
        # raise exceptions.UserError(_(self.env.user))
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id

        return result

class DistributionPaymentRequest(models.Model):
    _name = 'distribution.payment.request'
    _description = 'Distribution Payment Request'

    request_id = fields.Many2one(comodel_name="change.payroll.request", string="Employee Request", required=False, )

    is_balance_to = fields.Boolean(string="Balance to", )

    # Cash
    office_id = fields.Many2one(comodel_name="fh.office", string="Local FH Office", required=False, )

    amount = fields.Integer(string="Amount", required=False, min=1)

    distribution = fields.Selection(string="Distribution", selection=[('wire', 'Wire'),
                                                   ('dep1', 'Deposit 1'),
                                                   ('dep2', 'Deposit 2'),
                                                   ('cash', 'Cash'),
                                                   ], required=False, )

class DescriptionPension(models.Model):
    _name = 'description.pension'
    _description = 'Description Pension'

    name = fields.Char(string="Description", required=True, )
    code = fields.Char(string="Code", required=False, )
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 required=False, readonly=True, default=lambda self: self.env.user.company_id.id)


class ChangesEmployeeReport(models.Model):
    _name = 'changes.employee.report'
    _description = 'Changes Employee Report'

    type_change_id = fields.Many2one(comodel_name="changes.payroll.type", string="Type Of Change",
                                     required=True, domain=[('type_of', '=', 'employee')])
    file_action = fields.Binary(string="File", required=True)
    name = fields.Char(string="Name", required=False, related="type_change_id.name")
    amount = fields.Float(string="Amount", required=True, )
    date = fields.Date(string="Date", required=False, default=datetime.today())
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", required=False, )
    user_id = fields.Many2one(comodel_name="res.users", string="User", required=False,
                              default=lambda self: self.env.user.id)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 required=False, readonly=True, default=lambda self: self.env.user.company_id.id)

    payroll_request_id = fields.Many2one(comodel_name="change.payroll.request", string="Payroll Request", required=False, )

    name_file = fields.Char(string="File Name", required=False, )

    @api.model
    def default_get(self, field_list):
        result = super(ChangesEmployeeReport, self).default_get(field_list)
        # if 'employee_id' in field_list and result.get('user_id'):
        # raise exceptions.UserError(_(self.env.user))
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id

        return result


    @api.model
    def create(self, values):
        # Add code here
        employee = self.env['hr.employee'].search([('id', '=', values['employee_id'])])[0]
        contract = self.env['hr.contract'].search([('employee_id', '=', values['employee_id'])])

        if contract:
            values['contract_id'] = contract[0].id

        return super(ChangesEmployeeReport, self).create(values)

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    balance_to = fields.Selection(string="Balance To",
                                        selection=[('wire', 'Wire'),
                                                   ('dep1', 'Deposit 1'),
                                                   ('dep2', 'Deposit 2'),
                                                   ('cash', 'Cash'),
                                                   ], required=False, )
    pension_amount = fields.Float(string="Amount Pension", required=False, )
    description_pension_id = fields.Many2one(comodel_name="description.pension",
                                             string="Description Pension",
                                             required=False, )

class ConsolidateChangeReport(models.Model):
    _name = 'consolidate.change.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'


    name = fields.Char(string="Payroll Run", required=False, default=lambda self: self._get_name_default())
    date = fields.Date(string="Date", required=False, default=datetime.today())
    lines_ids = fields.One2many(comodel_name="consolidate.change.report.line", inverse_name="changes_payroll_id", string="Lines", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State", selection=[('draft', 'Created'),
                                                        ('submitted', 'Submitted'),
                                                        ('validated', 'Confirmed'),
                                                        ('processed', 'Processed')],
                             required=False,
                             default='draft', track_visibility='onchange' )
    year = fields.Selection(string='Year',
                            selection=[(year, str(year)) for year in range(2019, (datetime.now().year) + 2)],
                            required=False, )
    month = fields.Selection(string='Month',
                             selection=[(1, 'Jan'),
                                        (2, 'Feb'),
                                        (3, 'Mar'),
                                        (4, 'Apr'),
                                        (5, 'May'),
                                        (6, 'Jun'),
                                        (7, 'Jul'),
                                        (8, 'Aug'),
                                        (9, 'Sep'),
                                        (10, 'Oct'),
                                        (11, 'Nov'),
                                        (12, 'Dec'),
                                        ],
                             required=False, )

    def _get_name_default(self):
        year = datetime.now().year
        month = datetime.now().month

        month_dict = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
                      7: 'July', 8: 'August',
                      9: 'September', 10: 'October', 11: 'November', 12: 'December'}

        company_code = self.env.user.company_id.business_unit_code
        name_record = company_code + ' ' + "One-time changes" + ' ' + str(year) + ' ' + str(month_dict[month])

        old_name_report = self.search([('name', '=like', name_record + '%')])

        if old_name_report:
            name_record = name_record + ' ' + str(len(old_name_report) + 1)

        return name_record

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(ConsolidateChangeReport, self).fields_get(allfields, attributes=attributes)

        no_fields = ['id', 'name', 'code', 'date_start', 'date_end', ]

        for field in res.keys():

            if not field in no_fields:

                if res.get(field):
                    res.get(field)['searchable'] = False

        return res

    def delete_lines_load(self):

        lines = self.env['consolidate.change.report.line'].search(
            [('changes_payroll_id', '=', self.id)]
        )

        if lines:
            lines.unlink()


    def create_changes_by_employee(self):

        period = self.get_period(self.month, self.year)

        one_time_changes = self.env['changes.payroll'].search([
            ('date', '>=', period[0]),
            ('date', '<=', period[1]),
            ('company_id', '=', self.company_id.id)]
        )

        message = ''

        error = False

        for one in one_time_changes:
            if one.state != 'validated':
                message = message + 'One-Time Changes Process  Is Pending To Validate %s\n' % (one.name)
                error = True


        if error:
            raise exceptions.UserError(_(message))

        self.delete_lines_load()

        dict_month = {
            1: '31', 2: '28', 3: '31', 4: '30', 5: '31', 6: '30', 7: '31', 8: '31', 9: '30', 10: '31', 11: '30',
            12: '31'
        }

        # date = self.date.split('-')
        # date_from = date[0] + '-' + date[1] + '-' + '01'
        # date_to = date[0] + '-' + date[1] + '-' + dict_month[int(date[1])]
        date_from = period[0]
        date_to = period[1]

        onetime_lines = self.env['changes.payroll.line'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'validated'),
        ])

        # raise exceptions.UserError(_(onetime_lines))

        for line in onetime_lines:
            self.env['consolidate.change.report.line'].create(
                    {
                        'type_change_id': line.type_change_id.id,
                        'employee_id': line.employee_id.id,
                        'amount': line.amount,
                        # 'pension_percentage': line.pension_percentage,
                        # 'pension_percentage_calc': line.pension_percentage_calc,
                        'apply_on': line.apply_on,
                        'changes_payroll_id': self.id,
                        'contract_id': line.contract_id.id,
                        'date': line.date,
                        'file_action': line.file_action,
                        'name_file': line.name_file,
                        'one_time_id': line.changes_payroll_id.id,
                        'type_line': 'onetime',
                        'percent': line.percent
                    }
                )

        requests = self.env['change.payroll.request'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
        ])

        for request in requests:

            for line in request.lines_ids:
                self.env['consolidate.change.report.line'].create(
                    {
                        'type_change_id': line.type_change_id.id,
                        'employee_id': line.employee_id.id,
                        'amount': line.amount,
                        # 'pension_percentage': line.pension_percentage,
                        # 'pension_percentage_calc': line.pension_percentage_calc,
                        'apply_on': '3',
                        'changes_payroll_id': self.id,
                        'contract_id': line.contract_id.id,
                        'date': line.date,
                        'file_action': line.file_action,
                        'name_file': line.name_file,
                        'type_line': 'request'
                    }
                )

        personal_actions = self.env['changes.payroll.fixed.line'].search([
            ('company_id', '=', self.company_id.id),
            ('date_from', '<=', date_to),
            ('date_from', '>=', date_from),
            ('state', '=', 'validated')
        ])

        for action in personal_actions:

            self.env['consolidate.change.report.line'].create(
                {
                    'type_change_id': action.type_change_id.id,
                    'employee_id': action.employee_id.id,
                    'amount': action.amount,
                    # 'pension_percentage': action.pension_percentage,
                    # 'pension_percentage_calc': action.pension_percentage_calc,
                    'apply_on': action.apply_on,
                    'changes_payroll_id': self.id,
                    'contract_id': action.contract_id.id,
                    'date': action.date_from,
                    'type_line': 'personal',
                    'percent': action.percent,
                }
            )

        hr_salary_history = self.env['hr.contract.salary'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '<=', date_to),
            ('date', '>=', date_from),
            ('state', '=', 'validate')

        ])

        for salary in hr_salary_history:
            concept_s = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                               ('type_of', '=', 'wage')], limit=1)

            self.env['consolidate.change.report.line'].create(
                {
                    'type_change_id': concept_s.id,
                    'employee_id': salary.employee_id.id,
                    'amount': salary.amount,
                    # 'pension_percentage': salary.pension_percentage,
                    # 'pension_percentage_calc': salary.pension_percentage_calc,
                    'apply_on': '3',
                    'changes_payroll_id': self.id,
                    'contract_id': salary.contract_id.id,
                    'date': salary.date,
                    'type_line': 'wage'
                }
            )

        hr_contract_history = self.env['hr.contract'].search([
            ('company_id', '=', self.company_id.id),
            ('create_date', '<=', date_to),
            ('create_date', '>=', date_from),
            ('state', '=', 'draft')

        ])

        # for contract in hr_contract_history:
        #     concept_s = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
        #                                                          ('type_of', '=', 'position')], limit=1)
        #
        #     date = contract.create_date.split('-')[0] + '-' + contract.create_date.split('-')[1] + '-' + contract.create_date.split('-')[2]
        #
        #     self.env['consolidate.change.report.line'].create(
        #         {
        #             'type_change_id': concept_s.id,
        #             'employee_id': contract.employee_id.id,
        #             # 'amount': salary.amount,
        #             # 'pension_percentage': salary.pension_percentage,
        #             # 'pension_percentage_calc': salary.pension_percentage_calc,
        #             'apply_on': '3',
        #             'changes_payroll_id': self.id,
        #             'contract_id': contract.id,
        #             'date': date,
        #             'type_line': 'contract',
        #         }
        #     )

        hr_termination = self.env['hr.termination'].search([
            ('company_id', '=', self.company_id.id),
            ('date_termination', '<=', date_to),
            ('date_termination', '>=', date_from),
            ('state', '=', 'approved')

        ])

        for termination in hr_termination:
            concept_s = self.env['changes.payroll.type'].search([('company_id', '=', self.company_id.id),
                                                                 ('type_of', '=', 'termination')], limit=1)
            dict_payroll = {'a': '1', 'b': '2', 'special': '3'}

            self.env['consolidate.change.report.line'].create(
                {
                    'type_change_id': concept_s.id,
                    'employee_id': termination.employee_id.id,
                    # 'amount': salary.amount,
                    # 'pension_percentage': salary.pension_percentage,
                    # 'pension_percentage_calc': salary.pension_percentage_calc,
                    'apply_on': dict_payroll[termination.payroll_run],
                    'changes_payroll_id': self.id,
                    'contract_id': termination.employee_id.contract_id.id,
                    'date': termination.date_termination,
                    'type_line': 'personal',
                    'termination_id': termination.id
                }
            )



    def get_period(self, month, year):

        dict_month = {
        1: '31', 2: '28', 3: '31', 4: '30', 5: '31', 6: '30', 7: '31', 8: '31', 9: '30', 10: '31', 11: '30', 12: '31'
        }

        from_to = []
        month = str(month).zfill(2)
        year = str(year)

        from_to.append(year + '-' + month + '-' + '01')

        from_to.append(year + '-' + month + '-' + dict_month[int(month)])

        return from_to

    def approve_this(self):

        self.write({'state': 'validated'})

        one = []

        for line in self.lines_ids:
            line.write({'state': 'validated'})

            if line.one_time_id:
                if line.one_time_id.id not in one:
                    line.one_time_id.close_this()
                    one.append(line.one_time_id.id)

    def draft_this(self):
        self.write({'state': 'draft'})
        one = []

        for line in self.lines_ids:
            line.write({'state': 'draft'})

            if line.one_time_id:
                if line.one_time_id.id not in one:
                    line.one_time_id.approve_this()
                    one.append(line.one_time_id.id)

    def get_change(self,code, date, apply_on, employee):

        date_slt = date.split('-')
        date_from = date_slt[0] + '-' + date_slt[1] + '-' + '-' + '01'

        change = self.env['consolidate.change.report.line'].search([('employee_id', '=', employee),
                                                          ('date', '<=', date),
                                                          ('date', '>=', date_from),
                                                          ('code', '=', code),
                                                          ('apply_on', '=', apply_on)])
        plus = 0.0

        for c in change:
            plus = plus + c.amount

        return plus

class ConsolidateChangeReportLines(models.Model):
    _name = 'consolidate.change.report.line'
    _order = "date desc"


    type_change_id = fields.Many2one(comodel_name="changes.payroll.type", string="Type of change",
                                     required=False, domain=['|', ('type_of', '=', 'rule'),
                                                             ('type_of', '=', 'percentage')])
    code = fields.Char(string="Code of change", required=False, related="type_change_id.code")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False,
                                  )
    code_employee = fields.Char(string="Code of employee", required=False, related="employee_id.code")
    name = fields.Char(string="Name", required=False, related="type_change_id.name")
    amount = fields.Float(string="Amount",  required=False, )
    is_pension = fields.Selection(string="Is Pension?", selection=[('no', 'No'), ('yes', 'Yes')])
    pension_percentage = fields.Float(string="Pension Amount", required=False)
    pension_percentage_calc = fields.Char(string="Percentage", compute='_percentage_calculation')
    date = fields.Date(string="Date", required=False, default=datetime.today())
    apply_on = fields.Selection(string="Apply on", selection=[('1', 'First Period'),
                                                                ('2', 'Second Period'),
                                                                ('3', 'Month'), ],
                                required=False, )
    changes_payroll_id = fields.Many2one(comodel_name="consolidate.change.report", string="Main", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(string="State",
                             selection=[('draft', 'Draft'), ('validated', 'Validated')],
                             required=False,
                             default='draft')
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", required=False, )
    file_action = fields.Binary(string="File", )
    request_id = fields.Many2one(comodel_name="change.payroll.request", string="Employee Request", required=False, )
    name_file = fields.Char(string="File name", required=False, )
    type_line = fields.Selection(string="Type Line", selection=[('request', 'Employee Request'),
                                                                ('wage', 'Wage'),
                                                                ('personal', 'Personal Action'),
                                                                ('onetime', 'One-Time Change'),
                                                                ('contract', 'Contract'),
                                                                ], required=False, default='onetime')
    one_time_id = fields.Many2one(comodel_name="changes.payroll", string="One-time Change", required=False, )
    percent = fields.Float(
        string='Percent', 
        required=False)
    termination_id = fields.Many2one(
        comodel_name='hr.termination',
        string='Termination',
        required=False)

    @api.one
    def _percentage_calculation(self):
        if self.pension_percentage > 0:
            self.pension_percentage_calc = str(int(self.pension_percentage / 100)) + "%"


class HRPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    date_start = fields.Date(string="Date Start", required=False, readonly=True)
    date_end = fields.Date(string="Date End", required=False, readonly=True)
    payslip_run_id = fields.Many2one(comodel_name="hr.payslip.run", string="Payslip Run", required=False, )
    month = fields.Selection(string='Month',
                             selection=[('1', 'Jan'),
                                        ('2', 'Feb'),
                                        ('3', 'Mar'),
                                        ('4', 'Apr'),
                                        ('5', 'May'),
                                        ('6', 'Jun'),
                                        ('7', 'Jul'),
                                        ('8', 'Aug'),
                                        ('9', 'Sep'),
                                        ('10', 'Oct'),
                                        ('11', 'Nov'),
                                        ('12', 'Dec'),
                                        ],
                             required=False, readonly=True)
    year = fields.Selection(string='Year',
                            selection=[(year, str(year)) for year in range(2000, (datetime.now().year) + 1)],
                            required=False, readonly=True)


    @api.model
    def default_get(self, fields):
        res = super(HRPayslipEmployees, self).default_get(fields)
        active_id = self._context.get("active_id", False)
        if active_id:
            date = self.env["hr.payslip.run"].browse(active_id)
            message_date = date.create_date
            date_split_list = message_date.split("-")
            year = date_split_list[0]
            month = date_split_list[1]

            res.update({"date_start": date.date_start,
                        "date_end": date.date_end,
                        "year": int(year),
                        "month": str(int(month))
                        })
        return res

    @api.model
    def _fill_date(self):
        message_date = self.create_date
        date_payment_split_list = message_date.date.split("-")
        year = date_payment_split_list[0]
        month = date_payment_split_list[1]
        self.year = str(year)
        self.month = str(int(month))


    @api.multi
    def compute_sheet(self):
        self.date_start = self.payslip_run_id.date_start
        self.date_end = self.payslip_run_id.date_end

        message = ''

        one_time_changes = self.env['changes.payroll'].search([
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('company_id', '=', self.payslip_run_id.company_id.id)]
        )

        consolidates = self.env['consolidate.change.report'].search([
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('company_id', '=', self.payslip_run_id.company_id.id)]
        )

        error = False

        for one in one_time_changes:
            if one.state not in ('validated', 'close'):
                message = message + 'One-Time Changes Process  Is Pending To Validate %s\n' % (one.name)
                error = True

        for con in consolidates:
            if con.state != 'validated':
                message = message + 'Consolidate Changes Process Process  Is Pending To Validate %s\n' % (con.name)
                error = True


        if error:
            raise exceptions.UserError(_(message))
        else:
            payslips = self.env['hr.payslip']
            [data] = self.read()
            active_id = self.env.context.get('active_id')
            if active_id:
                [run_data] = self.env['hr.payslip.run'].browse(active_id).read(
                    ['date_start', 'date_end', 'credit_note'])
            from_date = run_data.get('date_start')
            to_date = run_data.get('date_end')
            if not data['employee_ids']:
                raise UserError(_("You must select employee(s) to generate payslip(s)."))
            for employee in self.env['hr.employee'].browse(data['employee_ids']):
                slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id,
                                                                        contract_id=False)
                run_payslip = self.env['hr.payslip.run'].browse(active_id)
                name = str(employee.code) + '-' + run_payslip.name
                res = {
                    'employee_id': employee.id,
                    'name': name,
                    'struct_id': slip_data['value'].get('struct_id'),
                    'contract_id': slip_data['value'].get('contract_id'),
                    'payslip_run_id': active_id,
                    'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                    'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                    'date_from': from_date,
                    'date_to': to_date,
                    'credit_note': run_data.get('credit_note'),
                    'company_id': employee.company_id.id,
                }
                payslips += self.env['hr.payslip'].create(res)
            payslips.compute_sheet()
            return {'type': 'ir.actions.act_window_close'}


        # raise exceptions.UserError(_(self.date_start))











