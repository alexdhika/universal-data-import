{
    'name': 'Universal Data Import',
    'summary': "Surya Semesta Modul Universal Data Import",

    'description': """
Tools untuk mengimpor data dari DB lain ke Odoo.
    """,

    'author': "Surya Semesta Dev Team",
    'website': "https://www.suryasemesta.com",
    'license': 'OEEL-1',
    'version': '1.0',
    'depends': ['base','mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/import_types_views.xml',
        'views/data_source_config_views.xml',
        'views/menu.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'universal_data_import/static/src/css/kanban.css',
    #     ],
    # },
    'installable': True,
    'application': True,
}
