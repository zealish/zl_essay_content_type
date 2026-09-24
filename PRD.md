# PRD — Odoo 18 Community Addon: Essay Content Type for eLearning

Version: 1.0
Target: Odoo 18 Community
Module: website_slides_essay_content
Parent Module: website_slides
Status: Draft

---

# 1. Overview

## Objective

Create a new **Essay** content type for Odoo 18 Community eLearning (`website_slides`) that behaves similarly to the existing **Quiz** content type.

The Essay type allows students to answer long-form questions within a timed session. Unlike Quiz, grading is performed manually by instructors.

## Problem

Odoo Community provides Video, Article, and Quiz content types, but it lacks a native essay/subjective assessment feature. Institutions and training providers need written assessments that integrate directly into course progress.

## Success Criteria

- New Essay content type appears alongside Quiz.
- Timer works identically to Quiz.
- Students can submit one essay attempt.
- Automatic submission occurs when time expires.
- Instructors can manually grade and provide feedback.
- Grades are reflected in course progress.

---

# 2. Goals

## Functional Goals

- Add Essay as a new slide content type.
- Support timed writing sessions.
- Persist timer server-side.
- Manual grading workflow.
- Student feedback and score.
- Integrate with learning progress.

## Non-Goals

- AI grading
- Rubric grading
- Multiple essay questions per slide
- File attachments
- Rich text editing
- Peer review

---

# 3. User Roles

## Student

- Start essay
- Write answer
- Submit answer
- View score and feedback after grading

## Instructor

- Create essay slide
- Configure timer and score
- Review submissions
- Grade essays
- Publish results

## Administrator

- Full access to configuration and records

---

# 4. User Flow

## Student Flow

1. Open Essay slide.
2. Read instructions.
3. Click **Start Essay**.
4. Timer begins.
5. Write answer.
6. Submit before timer ends.
7. If timer reaches zero, system auto-submits.
8. Wait for instructor grading.
9. View score and feedback.

## Instructor Flow

1. Create new slide.
2. Select **Content Type = Essay**.
3. Enter question.
4. Set time limit.
5. Set maximum score.
6. Publish slide.
7. Review submissions.
8. Grade and provide feedback.

---

# 5. Functional Requirements

## FR-01 Content Type

A new content type named **Essay** must appear in the slide type selector.

Display name:

- Essay

Icon:

- fa-file-text-o

Behavior should follow Quiz wherever applicable.

---

## FR-02 Essay Configuration

Each Essay slide contains the following fields.

| Field                | Type    | Required |
| -------------------- | ------- | -------- |
| Title                | Char    | Yes      |
| Question             | HTML    | Yes      |
| Time Limit (minutes) | Integer | Yes      |
| Maximum Score        | Float   | Yes      |
| Passing Score        | Float   | No       |
| Published            | Boolean | Yes      |

Time limit uses minutes, matching Quiz behavior.

---

## FR-03 Start Session

The timer does **not** begin when opening the page.

It begins only after the student clicks **Start Essay**.

System records:

- started_at
- expires_at
- state = in_progress

Only one active attempt is allowed.

---

## FR-04 Timer

Timer behavior must match Quiz.

Requirements:

- Countdown visible.
- Refreshing page keeps remaining time.
- Closing browser does not pause timer.
- Remaining time calculated from server timestamps.
- Client cannot modify remaining time.

When remaining time reaches zero:

- Lock editor
- Save latest answer
- Submit automatically

---

## FR-05 Writing Interface

Student interface contains:

- Essay title
- Instructions
- Countdown timer
- Question
- Character counter
- Large textarea
- Submit button

Textarea is plain text.

Autosave is optional for V1.

---

## FR-06 Submission

Student may submit manually before time expires.

Submission stores:

- answer
- submitted_at
- duration
- state = submitted

After submission:

- Editing is disabled.
- Timer stops.
- Student sees Pending Review status.

---

## FR-07 Auto Submit

When timer expires:

System automatically:

1. Save answer.
2. Set submitted_at.
3. Change state to submitted.
4. Prevent further editing.

Displayed message:

> Time is over. Your essay has been submitted automatically.

---

## FR-08 Manual Grading

Instructor grading page displays:

- Student
- Submission time
- Time spent
- Essay answer
- Score input
- Feedback textarea

Saving grade performs:

- state → graded
- score saved
- feedback saved
- course progress updated

---

## FR-09 Student Result

Before grading:

Status:

- Pending Review

Visible:

- Submission time
- Submitted answer

Hidden:

- Score
- Feedback

After grading:

Visible:

- Score
- Maximum score
- Passed/Failed
- Instructor feedback

---

# 6. Data Model

## Model: slide.slide.essay

Purpose:
Essay configuration attached to one slide.

Fields:

| Field         | Type                  |
| ------------- | --------------------- |
| slide_id      | Many2one(slide.slide) |
| question      | Html                  |
| time_limit    | Integer               |
| max_score     | Float                 |
| passing_score | Float                 |

---

## Model: slide.slide.essay.attempt

Purpose:
Student submission.

Fields:

| Field        | Type      |
| ------------ | --------- |
| essay_id     | Many2one  |
| user_id      | Many2one  |
| answer       | Text      |
| score        | Float     |
| feedback     | Text      |
| started_at   | Datetime  |
| submitted_at | Datetime  |
| expires_at   | Datetime  |
| state        | Selection |

States:

- draft
- in_progress
- submitted
- graded

Unique constraint:

One attempt per user per essay.

---

# 7. Progress Integration

Essay follows Quiz completion logic.

| State       | Progress  |
| ----------- | --------- |
| Draft       | 0%        |
| In Progress | 0%        |
| Submitted   | Completed |
| Graded      | Completed |

Passing score is informational only.

---

# 8. Backend Screens

## Essay Form

Contains:

- Title
- Question
- Time Limit
- Maximum Score
- Passing Score
- Publish

## Submission List

Columns:

- Student
- Started
- Submitted
- Status
- Score

Filters:

- In Progress
- Submitted
- Graded

## Grading Form

Sections:

1. Student Information
2. Essay Answer
3. Score
4. Feedback
5. Save Grade

---

# 9. Security

## Students

Permissions:

- Read own attempts
- Create own attempt
- Submit own attempt

Cannot:

- View other submissions
- Edit after submission
- Change score

## Instructors

Permissions:

- Read course attempts
- Grade attempts
- Edit feedback

## Administrators

Full CRUD access.

---

# 10. Technical Requirements

## Dependencies

- website_slides
- website
- mail

## Module Structure

website_slides_essay_content/

- **init**.py
- **manifest**.py
- models/
- controllers/
- views/
- security/
- static/

## Controllers

| Route                | Method | Purpose        |
| -------------------- | ------ | -------------- |
| /slides/essay/start  | POST   | Start attempt  |
| /slides/essay/save   | POST   | Save answer    |
| /slides/essay/submit | POST   | Manual submit  |
| /slides/essay/result | GET    | Student result |

---

# 11. Validation Rules

- Time limit must be greater than zero.
- Maximum score must be positive.
- Student cannot create multiple attempts.
- Submitted attempts are immutable.
- Score cannot exceed maximum score.
- Negative scores are not allowed.

---

# 12. Acceptance Criteria

| ID    | Requirement                              |
| ----- | ---------------------------------------- |
| AC-01 | Essay appears as a new content type      |
| AC-02 | Instructor can configure timer           |
| AC-03 | Student starts timed session manually    |
| AC-04 | Timer persists after page refresh        |
| AC-05 | Browser close does not pause timer       |
| AC-06 | Time expiration triggers auto submit     |
| AC-07 | Student cannot edit after submission     |
| AC-08 | Instructor can assign score and feedback |
| AC-09 | Student can view graded result           |
| AC-10 | Course progress updates after submission |

---

# 13. Future Enhancements

- Rich text editor
- Autosave every 30 seconds
- AI-assisted grading
- Rubric scoring
- Multiple essay questions
- File attachments
- Plagiarism detection
- Grade moderation workflow
