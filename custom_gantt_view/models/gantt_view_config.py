# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.tools import view_validation


class ViewExtended(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(
        selection_add=[('gantt_custom', "GanttView")]
    )


class WindowActionExtended(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(
        selection_add=[('gantt_custom', "GanttView")]
    )


@view_validation.validate('gantt_custom')
def validate_gantt_custom(arch):
    """add validation in the future"""
    return True


class GanttContents(models.Model):
    _name = 'custom.gantt.content'

    @api.model
    def fetch_gantt_contents(self, FieldsInfo, res_ids=False):
        if not FieldsInfo and not res_ids:
            return False
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        if res_ids == False:
            result = self.env[FieldsInfo['model']].search([
                (FieldsInfo['date_start'], '!=', None),
                (FieldsInfo['end_date'], '!=', None),
            ])
        else:
            result = self.env[FieldsInfo['model']].search([
                ('id', 'in', res_ids),
                (FieldsInfo['date_start'], '!=', None),
                (FieldsInfo['end_date'], '!=', None),
            ])
        task_array = {}
        for rec in result:
            type_field = rec[FieldsInfo['col']]
            if type_field.id not in task_array:
                task_array[type_field.id] = [{
                    'id': str(type_field.id),
                    'parent': True,
                    'child': False,
                    'type_id': type_field.id,
                    'rec_id': False,
                    'name': type_field[type_field._rec_name],
                    'start': rec[FieldsInfo['date_start']],
                    'end': rec[FieldsInfo['end_date']],
                    # 'dependencies': '',
                    'custom_class': 'bar-milestone'
                }, {
                    'id': str(rec.id),
                    'parent': False,
                    'child': True,
                    'type_id': type_field.id,
                    'rec_id': rec.id,
                    'name': rec[rec._rec_name],
                    'start': rec[FieldsInfo['date_start']],
                    'end': rec[FieldsInfo['end_date']],
                    'dependencies': str(type_field.id),
                    'custom_class': 'bar-milestone',
                }]
            elif type_field.id in task_array:
                temp = {
                    'id': str(rec.id) + str(type_field.id),
                    'child': True,
                    'parent': False,
                    'rec_id': rec.id,
                    'type_id': type_field.id,
                    'name': rec[rec._rec_name],
                    'start': rec[FieldsInfo['date_start']],
                    'end': rec[FieldsInfo['end_date']],
                    'dependencies': str(type_field.id),
                    'custom_class': 'bar-milestone',
                }
                task_array[type_field.id].append(temp)
                if rec[FieldsInfo['date_start']] < task_array[type_field.id][0]['start']:
                    task_array[type_field.id][0]['start'] = rec[FieldsInfo['date_start']]
                if rec[FieldsInfo['end_date']] > task_array[type_field.id][0]['end']:
                    task_array[type_field.id][0]['end'] = rec[FieldsInfo['end_date']]

        return [task_array, today]

    @api.model
    def update_time_range(self, task, result, start, end):
        """Updates time range"""
        model = result['model']
        if not task or not result:
            return False
        # fetch child record
        child_rec = self.env[model].search([('id', '=', task['rec_id'])])
        child_rec.write({
            result['date_start']: start,
            result['end_date']: end
        })
        return
