# -*- coding: utf-8 -*-
from odoo import http

# class MaintenanceCp(http.Controller):
#     @http.route('/maintenance_cp/maintenance_cp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maintenance_cp/maintenance_cp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('maintenance_cp.listing', {
#             'root': '/maintenance_cp/maintenance_cp',
#             'objects': http.request.env['maintenance_cp.maintenance_cp'].search([]),
#         })

#     @http.route('/maintenance_cp/maintenance_cp/objects/<model("maintenance_cp.maintenance_cp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maintenance_cp.object', {
#             'object': obj
#         })