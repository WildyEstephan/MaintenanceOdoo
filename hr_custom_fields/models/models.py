from odoo import api, fields, models
from datetime import datetime

class Employee(models.Model):
    _inherit = 'hr.employee'

    bank_id = fields.Many2one(comodel_name="res.bank", string="Bank", required=False, )
    code = fields.Char(string="Code", required=False, )
    first_lastname = fields.Char(string="First Last name", required=False, )
    names = fields.Char(string="First and Second Name", required=False, )
    second_lastname = fields.Char(string="Second Last Name", required=False, )
    tss_id = fields.Char(string="Social Number", required=False, )

class Contract(models.Model):
    _inherit = 'hr.contract'

    bonus = fields.Float(string="Bonus",  required=False, )
    hr_contract_salary_ids = fields.One2many(comodel_name="hr.contract.salary", inverse_name="contract_id", string="", required=False, )
    contract_year = fields.Integer(string="Years Worked", store=False, required=False, compute='_compute_years')
    contract_days = fields.Integer(string="Days Worked", required=False, compute='_compute_days')


    @api.multi
    def _compute_years(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        today = datetime.today()
        dt = datetime.strptime(self.date_start, '%Y-%m-%d')
        dt1 = today - dt
        dt2 = dt1.days

        self.contract_year = (dt2 / 365)

    @api.multi
    def _compute_days(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        today = datetime.today()
        dt = datetime.strptime(self.date_start, '%Y-%m-%d')
        dt1 = today - dt
        dt2 = dt1.days

        self.contract_days = dt2

    @api.one
    def onchange_wage(self):
        data = []
        for rec in self.hr_contract_salary_ids:
            if rec:
                if rec.concept == 'wage':
                    self.wage = rec.amount
                elif rec.concept == 'bonus':
                    self.bonus = rec.amount

class ContractSalary(models.Model):
    _name = 'hr.contract.salary'
    _description = 'HR Contract Salary'
    _order = "date asc"

    date = fields.Date(string="Date", required=True, )
    concept = fields.Selection(string="Concept", selection=[('wage', 'Wage'), ('bonus', 'Bonus'), ], required=True, )
    amount = fields.Float(string="Amount",  required=True, )
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", required=False, )

class Payslip(models.Model):
    _inherit = 'hr.payslip'

    payment_period = fields.Selection(string="Payment Period",
                             selection=[('1', 'First Period'), ('2', 'Second Period'), ('3', 'Both Periods'),],
                             required=False, related="payslip_run_id.payment_period")
    ss_key = fields.Selection(string="SS Key", selection=[('001', '001'), ('002', '002'), ], required=False, 
    related="payslip_run_id.ss_key")

class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    bank_id = fields.Many2one(comodel_name="res.bank", string="Bank", required=False, )
    company_id = fields.Many2one(comodel_name="res.company", string="Company", required=False, default=lambda self: self.env.user.company_id.id)
    payment_period = fields.Selection(string="Payment Period",
                                      selection=[('1', 'First Period'), ('2', 'Second Period'),
                                                 ('3', 'Both Periods'), ],
                                      required=False, )

    ss_key = fields.Selection(string="SS Key", selection=[('001', '001'), ('002', '002'), ], required=False,)


