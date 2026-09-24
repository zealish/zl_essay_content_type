from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import html2plaintext

class SlideEssay(models.Model):
    _name = 'slide.slide.essay'; _description = 'Essay Configuration'; _rec_name = 'question_preview'; _order = 'sequence, id'
    slide_id = fields.Many2one('slide.slide', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10, index=True)
    question = fields.Html(required=True, sanitize=True)
    question_preview = fields.Text(compute='_compute_question_preview')
    time_limit = fields.Integer('Time Limit (minutes)', required=True, default=30)
    max_score = fields.Float('Maximum Score', required=True, default=100.0)
    passing_score = fields.Float('Passing Score')
    attempt_ids = fields.One2many('slide.slide.essay.attempt', 'essay_id')
    _sql_constraints = [('time_positive','CHECK(time_limit > 0)','Time limit must be greater than zero.'),('max_positive','CHECK(max_score > 0)','Maximum score must be positive.'),('passing_nonnegative','CHECK(passing_score >= 0)','Passing score cannot be negative.')]
    @api.depends('question')
    def _compute_question_preview(self):
        for rec in self: rec.question_preview = html2plaintext(rec.question or '').strip()
    @api.constrains('passing_score','max_score')
    def _check_passing_score(self):
        for rec in self:
            if rec.passing_score > rec.max_score: raise ValidationError(_('Passing score cannot exceed maximum score.'))
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            slide = self.env['slide.slide'].browse(vals.get('slide_id')).exists()
            if not slide or slide.slide_category != 'essay': raise ValidationError(_('Essay configuration must belong to an Essay slide.'))
        return super().create(vals_list)
    def write(self, vals):
        for rec in self:
            if rec.attempt_ids and {'slide_id','time_limit'}.intersection(vals): raise UserError(_('Essay timing and ownership cannot change after an attempt exists.'))
        return super().write(vals)

class SlideEssayAttempt(models.Model):
    _name = 'slide.slide.essay.attempt'; _description = 'Essay Attempt'; _order = 'id'
    essay_id = fields.Many2one('slide.slide.essay', required=True, ondelete='cascade', index=True)
    slide_id = fields.Many2one(related='essay_id.slide_id', store=True, index=True)
    user_id = fields.Many2one('res.users', required=True, index=True, ondelete='restrict')
    answer = fields.Text(); score = fields.Float(); feedback = fields.Text()
    started_at = fields.Datetime(readonly=True); expires_at = fields.Datetime(readonly=True); submitted_at = fields.Datetime(readonly=True)
    remaining_seconds = fields.Integer(default=0, readonly=True); expired = fields.Boolean(readonly=True)
    duration = fields.Float(compute='_compute_duration', store=True)
    state = fields.Selection([('draft','Draft'),('paused','Paused'),('in_progress','In Progress'),('submitted','Submitted'),('graded','Graded')], default='draft', required=True, index=True)
    is_passed = fields.Boolean(compute='_compute_is_passed')
    _sql_constraints = [('one_attempt_per_user','unique(essay_id,user_id)','Only one attempt is allowed per user and essay.'),('score_nonnegative','CHECK(score >= 0)','Score cannot be negative.'),('remaining_nonnegative','CHECK(remaining_seconds >= 0)','Remaining time cannot be negative.')]
    @api.model_create_multi
    def create(self, vals_list):
        if not (self.env.user.has_group('website_slides.group_website_slides_officer') or self.env.user.has_group('base.group_system')):
            for vals in vals_list: vals['user_id'] = self.env.uid
        return super().create(vals_list)
    @api.depends('started_at','submitted_at')
    def _compute_duration(self):
        for rec in self: rec.duration = ((rec.submitted_at-rec.started_at).total_seconds()/60.0 if rec.started_at and rec.submitted_at else 0.0)
    @api.depends('score','essay_id.passing_score','state')
    def _compute_is_passed(self):
        for rec in self: rec.is_passed = rec.state == 'graded' and rec.score >= rec.essay_id.passing_score
    @api.constrains('score','essay_id')
    def _check_score(self):
        for rec in self:
            if rec.score < 0 or rec.score > rec.essay_id.max_score: raise ValidationError(_('Score must be between zero and the maximum score.'))
    @api.model
    def cron_expire_attempts(self):
        now = fields.Datetime.now()
        for attempt in self.search([('state','=','in_progress'),('expires_at','<=',now)]): attempt._expire(now)
    def _transition(self, vals): return super(SlideEssayAttempt, self.sudo()).write(vals)
    def _assert_owner(self):
        if any(rec.user_id != self.env.user for rec in self): raise AccessError(_('You can only change your own essay attempt.'))
    def _pause(self, now=None):
        self.ensure_one()
        if self.state != 'in_progress': return self
        now = now or fields.Datetime.now(); remaining = max(0, int((self.expires_at-now).total_seconds())) if self.expires_at else self.remaining_seconds
        self._transition({'state':'paused','remaining_seconds':remaining,'expires_at':False}); return self
    def _resume(self, now=None):
        self.ensure_one()
        if self.state not in ('draft','paused'): return self
        self._assert_owner(); now = now or fields.Datetime.now()
        remaining = self.essay_id.time_limit * 60 if self.state == 'draft' else self.remaining_seconds
        if remaining <= 0:
            self._transition({'state': 'submitted', 'submitted_at': now, 'expires_at': False,
                              'remaining_seconds': 0, 'expired': True})
            self.slide_id._essay_mark_completed(self.user_id)
            return self
        vals = {'state':'in_progress','expires_at':now+timedelta(seconds=remaining)}
        if self.state == 'draft': vals.update(started_at=now, remaining_seconds=remaining)
        self._transition(vals); return self
    def _expire(self, now=None):
        self.ensure_one()
        if self.state != 'in_progress': return False
        now = now or fields.Datetime.now()
        if self.expires_at and self.expires_at > now: return False
        self._transition({'state':'submitted','submitted_at':self.expires_at or now,'expires_at':False,'remaining_seconds':0,'expired':True})
        self.slide_id._essay_mark_completed(self.user_id); return True
    def save_answer(self, answer):
        self.ensure_one(); self._assert_owner()
        if self.state not in ('in_progress','paused'): raise UserError(_('This essay is no longer editable.'))
        if self.state == 'in_progress' and self.expires_at <= fields.Datetime.now(): self._expire(); raise UserError(_('The time limit has expired.'))
        super().write({'answer':answer or ''}); return self
    def start(self):
        self.ensure_one(); self._assert_owner()
        if self.state != 'draft': raise UserError(_('This essay attempt has already started.'))
        return self._resume()
    def submit(self, answer=None):
        self.ensure_one(); self._assert_owner()
        if self.state not in ('in_progress','paused'): raise UserError(_('This essay is no longer editable.'))
        if answer is not None: self.save_answer(answer)
        if self.state == 'in_progress' and self.expires_at <= fields.Datetime.now(): self._expire(); return self
        self._transition({'state':'submitted','submitted_at':fields.Datetime.now(),'expires_at':False,'remaining_seconds':0}); self.slide_id._essay_mark_completed(self.user_id); return self
    def grade(self, score, feedback=''):
        self.ensure_one()
        if not (self.env.user.has_group('website_slides.group_website_slides_officer') or self.env.user.has_group('base.group_system')): raise AccessError(_('Only instructors can grade essays.'))
        if self.state not in ('submitted','graded'): raise UserError(_('Only submitted essays can be graded.'))
        if score < 0 or score > self.essay_id.max_score: raise ValidationError(_('Score must be between zero and maximum.'))
        self._transition({'score':score,'feedback':feedback or '','state':'graded'}); return self
    def action_grade(self): self.grade(self.score,self.feedback); return True
    def write(self, vals):
        protected = {'user_id','essay_id','started_at','expires_at','submitted_at','remaining_seconds','state','expired','score','feedback'}
        for rec in self:
            if rec.state in ('submitted','graded') and (protected|{'answer'}).intersection(vals): raise AccessError(_('Submitted attempts are immutable; use the grading action.'))
            if protected.intersection(vals): raise AccessError(_('Attempt metadata can only be changed by its workflow.'))
        return super().write(vals)
