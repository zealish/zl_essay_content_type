# zl_essay_content_type

Timed, manually graded essay assessments for Odoo 18 eLearning (`website_slides`).

## Overview

Odoo Community ships Video, Article, and Quiz slide types but has no native long-form written assessment. This module adds an **Essay** content type that integrates directly into course slides — complete with a countdown timer, one-attempt-per-student constraint, and an instructor grading workflow.

## Features

| Feature | Description |
|---|---|
| Essay slide type | New content type alongside Quiz, Video, Article |
| Timed sessions | Server-side countdown per essay; auto-submits on expiry |
| One attempt per student | Enforced at DB level (`unique(essay_id, user_id)`) |
| Manual grading | Instructors score and leave feedback from the backend |
| Course progress | Slide marked complete after all essays are graded (or passed) |
| Pause / Resume | Closing the browser pauses the timer; resuming restores remaining time |
| Cron expiry | Scheduled job auto-expires stale in-progress attempts |
| Fullscreen player | Works inside the `website_slides` fullscreen mode |

## Dependencies

- `website_slides`
- `website`
- `mail`

## Installation

1. Place (or symlink) `zl_essay_content_type` inside your Odoo `addons` path.
2. Update the module list: **Apps → Update Apps List**.
3. Search for **Essay Content Type** and click **Install**.

### Docker

```bash
docker compose exec odoo odoo -u zl_essay_content_type -d <database>
```

## Usage

### Instructor

1. Open a course and create a new slide.
2. Set **Content Type** to **Essay**.
3. Add one or more essay questions under the **Essay** tab — each with a time limit and max score.
4. Publish the slide.
5. Review submissions via **eLearning → Essay Submissions**.
6. Open a submission, enter a score and feedback, click **Save Grade**.

### Student

1. Navigate to an essay slide and click **Start Essay**.
2. A per-question countdown begins immediately.
3. Type your answer; it auto-saves every 800 ms of inactivity.
4. Click **Next** / **Previous** to navigate between questions (timer pauses for the active question).
5. Click **Submit All Answers** when done (or wait for auto-submit on expiry).
6. After the instructor grades, your score and feedback appear on the result page.

## Data Models

| Model | Purpose |
|---|---|
| `slide.slide.essay` | Essay configuration (question, time limit, scores) attached to a slide |
| `slide.slide.essay.attempt` | One attempt per student per essay — answer, timing, grading state |

### Attempt Lifecycle

```
draft → in_progress → submitted → graded
              ↕
            paused
```

## Security

| Group | Essay Config | Attempts |
|---|---|---|
| Portal / Internal user | — | Read own, create own |
| eLearning Officer | CRUD | CRUD |
| Administrator | CRUD | CRUD (all records) |

Record rules scope attempts to the student's own records, the course instructor's records, or all records for admins.

## Cron Job

**Expire essay attempts** runs every minute and transitions any `in_progress` attempt whose `expires_at` has passed to `submitted`.

## Assets

| File | Bundle |
|---|---|
| `static/src/js/essay.js` | `web.assets_frontend` |
| `static/src/scss/essay.scss` | `web.assets_frontend` |

## Migration

`migrations/18.0.1.1.0/post-migrate.py` drops the former single-essay-per-slide constraint to support multiple questions per slide.

## License

LGPL-3
