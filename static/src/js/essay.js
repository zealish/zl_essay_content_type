/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

publicWidget.registry.Essay = publicWidget.Widget.extend({
  selector: '.o_wslides_essay',
  events: {
    'click .js_essay_start': '_startAssessment',
    'click .js_essay_next': '_next',
    'click .js_essay_prev': '_previous',
    'click .js_essay_finish': '_finish',
    'input .js_essay_answer': '_input',
  },
  async start() {
    await this._super(...arguments);
    document.querySelector('.o_wslides_fs_sidebar_list_item.active')?.closest('.o_wslides_fs_sidebar_section_slides')?.classList.add('show');
    this.items = [...this.el.querySelectorAll('.o_wslides_essay_item')];
    this.revision = 0;
    this.state = null;
    if (this.el.dataset.public !== '1' && this.items.length) await this._request('status');
  },
  destroy() {
    clearTimeout(this.clock);
    clearTimeout(this.saveTimer);
    return this._super(...arguments);
  },
  _startAssessment() { return this._request('start'); },
  _next() { return this._request('next'); },
  _previous() { return this._request('previous'); },
  _finish() { return this._request('submit'); },
  _input() {
    this.revision = (this.revision || 0) + 1;
    this._buttons();
    clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => this._request('save'), 800);
  },
  _request(action) {
    this.requestChain = (this.requestChain || Promise.resolve()).then(() => this._requestNow(action));
    return this.requestChain;
  },
  async _requestNow(action) {
    if (this.isDestroyed()) return;
    try {
      const revision = this.revision || 0;
      this.busy = true;
      this._buttons();
      const visibleItem = this.items.find(item => !item.classList.contains('d-none'));
      const current = this.state?.active_id || Number(visibleItem?.dataset.essayId) || null;
      const answer = this.items.find(item => Number(item.dataset.essayId) === current)?.querySelector('textarea')?.value;
      const params = { slide_id: Number(this.el.dataset.slideId), action };
      if (current) params.essay_id = current;
      if (answer !== undefined && action !== 'status') params.answer = answer;
      try {
        const state = await rpc('/slides/essay/session', params);
        this.state = state;
        this.receivedAt = performance.now();
        this.el.querySelector('.js_essay_error').classList.add('d-none');
        for (const question of state.questions) {
          const item = this.items.find(entry => Number(entry.dataset.essayId) === question.id);
          if (!item) continue;
          const textarea = item.querySelector('textarea');
          const isCurrent = question.id === state.active_id;
          if (!(action === 'save' && revision !== (this.revision || 0) && current === question.id)) textarea.value = question.answer || '';
          textarea.disabled = state.finished || question.expired;
          item.querySelector('.js_essay_expired').classList.toggle('d-none', !question.expired);
          item.classList.toggle('d-none', !isCurrent);
        }
        this.el.querySelector('.js_essay_intro').classList.toggle('d-none', state.started);
        this.el.querySelector('.js_essay_workspace').classList.toggle('d-none', !state.started || state.finished);
        this.el.querySelector('.js_essay_finished').classList.toggle('d-none', !state.finished);
        this._tick();
      } catch (error) {
        if (!this.isDestroyed()) {
          const message = this.el.querySelector('.js_essay_error');
          message.textContent = error.data?.message || error.message || 'Unable to save. Please try again.';
          message.classList.remove('d-none');
        }
      } finally {
        this.busy = false;
        if (!this.isDestroyed()) {
          this._buttons();
          if (revision !== (this.revision || 0)) this.saveTimer = setTimeout(() => this._request('save'), 800);
        }
      }
    } catch (_) {
      // Prevent pre-try errors from killing the promise chain
    }
  },
  _buttons() {
    this.el.querySelectorAll('button').forEach(button => { button.disabled = Boolean(this.busy); });
    if (!this.state) return;
    const index = this.state.questions.findIndex(question => question.id === this.state.active_id);
    const current = this.state.questions[index];
    const answer = this.items.find(item => Number(item.dataset.essayId) === current?.id)?.querySelector('textarea')?.value.trim();
    const previous = this.el.querySelector('.js_essay_prev');
    const next = this.el.querySelector('.js_essay_next');
    const submit = this.el.querySelector('.js_essay_finish');
    previous.classList.toggle('d-none', index <= 0);
    next.classList.toggle('d-none', index === this.items.length - 1);
    submit.classList.toggle('d-none', index !== this.items.length - 1);
    next.disabled = submit.disabled = Boolean(this.busy || (!answer && !current?.expired));
  },
  _tick() {
    clearTimeout(this.clock);
    if (!this.el.isConnected || !this.state?.started || this.state.finished) return;
    const question = this.state.questions.find(entry => entry.id === this.state.active_id);
    if (!question) return;
    const remaining = Math.max(0, question.remaining_seconds - (question.active ? (performance.now() - this.receivedAt) / 1000 : 0));
    const seconds = Math.ceil(remaining);
    const item = this.items.find(entry => Number(entry.dataset.essayId) === question.id);
    item.querySelector('.js_essay_timer').textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    if (remaining <= 0 && question.active && !this.busy) {
      this._request('expire');
    }
    this.clock = setTimeout(() => this._tick(), 500);
  },
});

Fullscreen.include({
  _fetchSlideContent() {
    if (this._slideValue.category !== 'essay') return this._super(...arguments);
    const slide = this._slideValue;
    return rpc('/slides/essay/fullscreen_content', { slide_id: slide.id }).then(data => {
      slide.htmlContent = data.html_content;
    });
  },
  async _renderSlide() {
    if (this.essayWidget) {
      this.essayWidget.destroy();
      this.essayWidget = null;
    }
    if (this._slideValue.category !== 'essay') return this._super(...arguments);
    if (this._renderSlideRunning) return;
    this._renderSlideRunning = true;
    try {
      const content = this.$('.o_wslides_fs_content').empty();
      content.html(this._slideValue.htmlContent);
      this.essayWidget = new publicWidget.registry.Essay(this);
      await this.essayWidget.attachTo(content.find('.o_wslides_essay'));
    } finally {
      this._renderSlideRunning = false;
    }
  },
});
