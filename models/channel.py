from odoo import fields, models

class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    nbr_essay = fields.Integer('Essays', compute='_compute_slides_statistics', store=True)

class SlideSlideStatistics(models.Model):
    _inherit = 'slide.slide'

    nbr_essay = fields.Integer('Number of Essays', compute='_compute_slides_statistics', store=True)
