# -*- coding: utf-8 -*-
from odoo import http

# class ChangesOfPayroll(http.Controller):
#     @http.route('/changes_of_payroll/changes_of_payroll/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/changes_of_payroll/changes_of_payroll/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('changes_of_payroll.listing', {
#             'root': '/changes_of_payroll/changes_of_payroll',
#             'objects': http.request.env['changes_of_payroll.changes_of_payroll'].search([]),
#         })

#     @http.route('/changes_of_payroll/changes_of_payroll/objects/<model("changes_of_payroll.changes_of_payroll"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('changes_of_payroll.object', {
#             'object': obj
#         })