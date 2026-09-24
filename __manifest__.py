{
    'name': 'Essay Content Type',
    'version': '18.0.1.2.0',
    'category': 'eLearning',
    'summary': 'Timed manually graded essay assessments for eLearning',
    'author': 'Zealish',
    'depends': ['website_slides', 'website', 'mail'],
    'data': [
        'security/essay_security.xml',
        'security/ir.model.access.csv',
        'data/essay_cron.xml',
        'views/slide_views.xml',
        'views/essay_views.xml',
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': ['zl_essay_content_type/static/src/js/essay.js', 'zl_essay_content_type/static/src/scss/essay.scss'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
