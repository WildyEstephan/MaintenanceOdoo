# -*- coding: utf-8 -*-
{
    'name': "Maintenance CP",

    'summary': """
        Maintenance Corrective and Preventive""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Wildy Estephan",
    'website': "http://www.westephan.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_invoicing', 'stock', 'hr', 'account_asset'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/groups_security.xml',
        'views/menus.xml',
        'views/asset.xml',
        'views/task_operation.xml',
        'views/equipment.xml',
        'views/product_view.xml',
        'views/team_quipment.xml',
        'views/workorder.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}