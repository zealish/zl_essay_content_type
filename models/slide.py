from odoo import api, fields, models


class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    slide_category = fields.Selection(selection_add=[('essay', 'Essay')], ondelete={'essay': 'cascade'})
    slide_type = fields.Selection(selection_add=[('essay', 'Essay')], ondelete={'essay': 'cascade'})
    essay_ids = fields.One2many('slide.slide.essay', 'slide_id', string='Essay Configuration', copy=False)

    @api.depends('slide_category', 'source_type', 'video_source_type')
    def _compute_slide_type(self):
        super()._compute_slide_type()
        for slide in self:
            if slide.slide_category == 'essay':
                slide.slide_type = 'essay'

    @api.depends('slide_type')
    def _compute_slide_icon_class(self):
        super()._compute_slide_icon_class()
        for slide in self:
            if slide.slide_type == 'essay':
                slide.slide_icon_class = 'fa-file-text-o'

    def _essay_mark_completed(self, user):
        self.ensure_one()
        if not user or user._is_public():
            return
        essays = self.essay_ids
        attempts = self.env['slide.slide.essay.attempt'].sudo().search([('essay_id', 'in', essays.ids), ('user_id', '=', user.id)])
        if not essays or set(attempts.mapped('essay_id').ids) != set(essays.ids) or any(attempt.state not in ('submitted', 'graded') for attempt in attempts):
            return
        partner = self.env['slide.slide.partner'].sudo().search([('slide_id', '=', self.id), ('partner_id', '=', user.partner_id.id)], limit=1)
        if partner:
            if not partner.completed:
                partner.write({'completed': True})
        else:
            self.env['slide.slide.partner'].sudo().create({'slide_id': self.id, 'partner_id': user.partner_id.id, 'completed': True})
