# -*- coding: utf-8 -*-
from odoo import http

# class RequisitionMaintenanceIntegration(http.Controller):
#     @http.route('/requisition_maintenance_integration/requisition_maintenance_integration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/requisition_maintenance_integration/requisition_maintenance_integration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('requisition_maintenance_integration.listing', {
#             'root': '/requisition_maintenance_integration/requisition_maintenance_integration',
#             'objects': http.request.env['requisition_maintenance_integration.requisition_maintenance_integration'].search([]),
#         })

#     @http.route('/requisition_maintenance_integration/requisition_maintenance_integration/objects/<model("requisition_maintenance_integration.requisition_maintenance_integration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('requisition_maintenance_integration.object', {
#             'object': obj
#         })