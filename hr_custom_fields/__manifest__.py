# -*- coding: utf-8 -*-
{
    'name': "HR Custom Fields",

    'summary': """
        Add some field for Humans Resources""",

    'description': """
        Add some field for Humans Resources
    """,

    'author': "Wildy Estephan",
    'website': "https://www.wildyestephan.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'hr','hr_payroll_account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}