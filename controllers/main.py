from odoo import fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from psycopg2 import IntegrityError


class EssayController(http.Controller):
    def _slide(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id)).exists()
        if (not slide or slide.slide_category != 'essay' or not slide.active or not slide.is_published
                or not slide.channel_id.can_access_from_current_website() or not slide.has_access('read')):
            raise AccessError('Essay is not available.')
        return slide

    def _attempt(self, attempt_id):
        attempt = request.env['slide.slide.essay.attempt'].search([
            ('id', '=', int(attempt_id)), ('user_id', '=', request.env.uid),
        ], limit=1)
        if not attempt:
            raise AccessError('Essay attempt not found.')
        self._slide(attempt.slide_id.id)
        return attempt

    def _essay(self, slide, essay_id):
        essay = slide.essay_ids.filtered(lambda rec: rec.id == int(essay_id))
        if not essay:
            raise AccessError('Essay question is not available.')
        return essay[0]

    @http.route('/slides/essay/fullscreen_content', type='json', auth='public', website=True)
    def essay_fullscreen_content(self, slide_id):
        slide = self._slide(slide_id)
        return {'html_content': request.env['ir.qweb']._render(
            'zl_essay_content_type.lesson_content_essay', {'slide': slide})}

    def _get_or_create_attempt(self, essay):
        Attempt = request.env['slide.slide.essay.attempt']
        attempt = Attempt.search([('essay_id', '=', essay.id), ('user_id', '=', request.env.uid)], limit=1)
        if attempt:
            return attempt
        try:
            with request.env.cr.savepoint():
                return Attempt.sudo().create({'essay_id': essay.id, 'user_id': request.env.uid})
        except IntegrityError as error:
            if error.diag.constraint_name != 'slide_slide_essay_attempt_one_attempt_per_user':
                raise
            return Attempt.search([('essay_id', '=', essay.id), ('user_id', '=', request.env.uid)], limit=1)

    def _attempts(self, slide):
        return request.env['slide.slide.essay.attempt'].search([
            ('essay_id', 'in', slide.essay_ids.ids), ('user_id', '=', request.env.uid),
        ]).sorted(lambda rec: (rec.essay_id.sequence, rec.essay_id.id))

    def _session_data(self, slide, attempts, active=None):
        now = fields.Datetime.now()
        # Expiry is always server authoritative, including refresh/status requests.
        for attempt in attempts:
            if attempt.state == 'in_progress' and attempt.expires_at and attempt.expires_at <= now:
                attempt._expire(now)
        active = active if active and active.state in ('in_progress', 'paused') else next(
            (a for a in attempts if a.state == 'in_progress'), None)
        if not active:
            active = next((a for a in attempts if a.state == 'paused'), None)
        if not active and any(a.started_at for a in attempts):
            active = next((a for a in attempts if a.state not in ('submitted', 'graded')), None)
        questions = []
        for attempt in attempts:
            remaining = attempt.remaining_seconds or 0
            if attempt.state == 'in_progress' and attempt.expires_at:
                remaining = max(0, int((attempt.expires_at - now).total_seconds()))
            questions.append({
                'id': attempt.essay_id.id,
                'attempt_id': attempt.id,
                'state': attempt.state,
                'answer': attempt.answer or '',
                'remaining_seconds': remaining,
                'active': bool(active and attempt.id == active.id),
                'expired': bool(attempt.expired),
            })
        finished = bool(questions) and all(q['state'] in ('submitted', 'graded') for q in questions)
        return {
            'started': any(a.started_at for a in attempts),
            'finished': finished,
            'active_id': active.essay_id.id if active else False,
            'questions': questions,
            'server_now': fields.Datetime.now().isoformat(),
        }

    def _validate_current(self, slide, attempts, essay_id):
        if essay_id is None:
            raise ValidationError('A current essay question is required.')
        essay = self._essay(slide, essay_id)
        attempt = next((a for a in attempts if a.essay_id.id == essay.id), None)
        if not attempt:
            raise AccessError('Essay attempt not found.')
        if attempt.state == 'in_progress' and attempt.expires_at <= fields.Datetime.now():
            attempt._expire()
        return attempt

    @http.route('/slides/essay/session', type='json', auth='user', website=True)
    def essay_session(self, slide_id, action='status', essay_id=None, answer=None):
        slide = self._slide(slide_id)
        attempts = self._attempts(slide)
        by_essay = {a.essay_id.id: a for a in attempts}
        # Create records without starting timers; status is intentionally side-effect-free re timer.
        for essay in slide.essay_ids.sorted(lambda rec: (rec.sequence, rec.id)):
            if essay.id not in by_essay:
                attempt = self._get_or_create_attempt(essay)
                attempts |= attempt
        attempts = attempts.sorted(lambda rec: (rec.essay_id.sequence, rec.essay_id.id))
        current = self._validate_current(slide, attempts, essay_id) if essay_id is not None else None

        if action == 'status':
            return self._session_data(slide, attempts, current)
        if action == 'start':
            if any(a.started_at for a in attempts):
                return self._session_data(slide, attempts, current)
            target = current or attempts[0]
            target.start()
            return self._session_data(slide, attempts, target)
        if not current:
            raise ValidationError('A current essay question is required.')
        if answer is not None and current.state in ('in_progress', 'paused'):
            current.save_answer(answer)

        index = attempts.ids.index(current.id)
        if action == 'save':
            return self._session_data(slide, attempts, current)
        if action == 'previous':
            if index == 0:
                raise UserError('There is no previous question.')
            target = attempts[index - 1]
            if not target.started_at:
                raise UserError('Previous questions must have been visited.')
            if current.state == 'in_progress':
                current._pause()
            target._resume()
            return self._session_data(slide, attempts, target)
        if action == 'next':
            if not (current.answer or '').strip() and not current.expired:
                raise ValidationError('Answer the current question before continuing.')
            target_index = index + 1
            while target_index < len(attempts) and attempts[target_index].state in ('submitted', 'graded'):
                target_index += 1
            if target_index >= len(attempts):
                raise UserError('This is the last question; submit the assessment.')
            if current.state == 'in_progress':
                current._pause()
            target = attempts[target_index]
            target._resume()
            return self._session_data(slide, attempts, target)
        if action == 'expire':
            if current.state == 'in_progress' and current.expires_at > fields.Datetime.now():
                raise UserError('The current question has not expired.')
            current._expire()
            if index < len(attempts) - 1:
                target = attempts[index + 1]
                target._resume()
                return self._session_data(slide, attempts, target)
            # Expiry of the last question atomically closes the whole assessment.
            now = fields.Datetime.now()
            for attempt in attempts:
                if attempt.state in ('draft', 'paused', 'in_progress'):
                    if attempt.state == 'in_progress':
                        attempt._expire(now)
                    elif attempt.answer or attempt.expired:
                        attempt._transition({'state': 'submitted', 'submitted_at': now,
                                             'expires_at': False, 'remaining_seconds': 0})
            slide._essay_mark_completed(request.env.user)
            return self._session_data(slide, attempts)
        if action == 'submit':
            if index != len(attempts) - 1:
                raise UserError('Only the last question can submit the assessment.')
            if current.state == 'in_progress' and current.expires_at <= fields.Datetime.now():
                current._expire()
            for attempt in attempts:
                if attempt.state in ('draft', 'paused', 'in_progress') and not attempt.expired:
                    if not (attempt.answer or '').strip():
                        raise ValidationError('Answer every question before submitting.')
            for attempt in attempts:
                if attempt.state in ('in_progress', 'paused'):
                    attempt.submit()
            return self._session_data(slide, attempts)
        raise ValidationError('Unknown essay session action.')

    @http.route('/slides/essay/result/<int:attempt_id>', type='http', auth='user', website=True)
    def essay_result(self, attempt_id):
        return request.render('zl_essay_content_type.essay_result', {'attempt': self._attempt(attempt_id)})
