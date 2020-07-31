from odoo import api, fields, models 
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta
from odoo import exceptions, _
from dateutil.relativedelta import relativedelta

class ChecklistTEmplate(models.Model):
    _name = 'checklist.template'
    _description = 'Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Name',
        required=False, related='equipment_id.name')
    equipment_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment',
        string='Equipment',
        required=True)
    frequency_exe = fields.Integer(string="Frequency Of Execution", required=True, default=1)
    frequency_time = fields.Selection(string="Frequency Time",
                                      selection=[('day', 'Days'),
                                                 ('week', 'Weeks'),
                                                 ('month', 'Months'),
                                                 ('year', 'Years'),
                                                 ], required=True, default='day')
    check_lines = fields.One2many(
        comodel_name='checklist.template.line',
        inverse_name='checklist_template_id',
        string='Check Lines',
        required=False)
    
    next_check = fields.Date(
        string='Next Check', 
        required=False)

    @api.model
    def update_check_date(self):

        records = self.env['checklist.template'].search()

        for rec in records:

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            day_man = ''
            new_date = ''

            day_start = datetime.strptime(rec.start_date, '%Y-%m-%d')

            if rec.next_check:
                day_man = rec.next_check

                if (not today_str == day_man) or (today_str < day_man):
                    if rec.frequency_time == 'day':
                        new_date = datetime.now() + relativedelta(days=rec.frequency_exe)
                    elif rec.frequency_time == 'week':
                        new_date = datetime.now() + relativedelta(weeks=rec.frequency_exe)
                    elif rec.frequency_time == 'month':
                        new_date = datetime.now() + relativedelta(months=rec.frequency_exe)
                    else:
                        new_date = datetime.now() + relativedelta(years=rec.frequency_exe)

                    rec.next_check = new_date.strftime('%Y-%m-%d')
            else:

                if rec.frequency_time == 'day':
                    new_date = datetime.now() + relativedelta(days=rec.frequency_exe)
                elif rec.frequency_time == 'week':
                    new_date = datetime.now() + relativedelta(weeks=rec.frequency_exe)
                elif rec.frequency_time == 'month':
                    new_date = datetime.now() + relativedelta(months=rec.frequency_exe)
                else:
                    new_date = datetime.now() + relativedelta(years=rec.frequency_exe)

                rec.next_check = new_date.strftime('%Y-%m-%d')

    @api.model
    def execute_all_planning(self):
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        records = self.env['checklist.template'].search([('next_check', '=', today_str)])

        for rec in records:
            rec.create_checklist()
    
    def create_checklist(self):
        user = self.equipment_id.specialist_id.user_id
        
        for template in self.check_lines:
            self.env['maintenance.checklist'].create(
                {
                    'item_id': template.item_id.id,
                    'name': template.name,
                    'equipment_id': self.equipment_id.id,
                    'user_id': user.id,
                    'metrics': template.metrics
                }
            )
            

class ChecklistItem(models.Model):
    _name = 'checklist.item'
    _description = 'Checklist Item'

    name = fields.Char(
        string='Name',
        required=True, )

class CheckLine(models.Model):
    _name = 'checklist.template.line'
    _description = 'CheckLine'

    item_id = fields.Many2one(
        comodel_name='checklist.item',
        string='Item',
        required=True)
    name = fields.Char(
        string='Name',
        required=True)
    equipment_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment',
        string='Equipment',
        required=False, related='checklist_template_id.equipment_id')
    metrics = fields.Boolean(
        string='Need Metrics',
        required=False)

    checklist_template_id = fields.Many2one(
        comodel_name='checklist.template',
        string='Checklist Template',
        required=False)

class Checklist(models.Model):
    _name = 'maintenance.checklist'
    _description = 'Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc'

    item_id = fields.Many2one(
        comodel_name='checklist.item',
        string='Item',
        required=True)
    name = fields.Char(
        string='Name',
        required=True)
    equipment_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment',
        string='Equipment',
        required=True, )
    date = fields.Date(
        string='Date', 
        required=False, default=datetime.now())
    done = fields.Boolean(
        string='Done', 
        required=False)
    maintenance_require = fields.Boolean(
        string='Maintenance Require',
        required=False)
    sumary = fields.Text(
        string="Summary",
        required=False)
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=False)
    metrics = fields.Boolean(
        string='Need Metrics',
        required=False)

    def done_this(self):
        # self.date = datetime.now()

        if self.metrics:
            action = self.env.ref('maintenance_cp.measure_wizard_action')
            result = action.read()[0]
            return result
        else:
            action = self.env.ref('maintenance_cp.checklist_wizard_action')
            result = action.read()[0]
            return result

        # self.done = True

class ChecklistWizard(models.TransientModel):
    _name = 'checklist.wizard'
    _description = 'Checklist Wizard'

    checklist_id = fields.Many2one(
        comodel_name='maintenance.checklist',
        string='Checklist',
        required=False)
    maintenance_require = fields.Boolean(
        string='Maintenance Require',
        required=False)
    sumary = fields.Text(
        string="Summary",
        required=False)

    def process(self):

        if self.maintenance_require:

            workorder = self.env['maintenance.cp.workorder'].sudo().create(
                {
                    'equipment_id': self.checklist_id.equipment_id.id,
                    'type_maintenance': 'corrective',
                    'description_problem': "Maintenance Corrective From Checklist: " + self.sumary,
                }
            )

        self.checklist_id.done = True
        self.checklist_id.maintenance_require = self.maintenance_require
        self.checklist_id.sumary = self.sumary

    @api.model
    def default_get(self, fields_list):

        res = super(ChecklistWizard, self).default_get(fields_list)

        checklist = self.env['maintenance.checklist'].search([('id', '=', self.env.context['active_id'])],
                                                             limit=1)
        # raise ValidationError((checklist.equipment_id.name))

        res['checklist_id'] = checklist.id

        return res

