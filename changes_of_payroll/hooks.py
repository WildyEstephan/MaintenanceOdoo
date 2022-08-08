from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, dict())
    task_obj = env['changes.payroll']
    sequence_obj = env['ir.sequence']
    tasks = task_obj.search([], order="id")
    for task_id in tasks.ids:
        cr.execute('UPDATE changes_of_payroll '
                   'SET change_payroll_sequence = %s '
                   'WHERE id = %s;',
                   (sequence_obj.next_by_code('changes.payroll'), task_id,))