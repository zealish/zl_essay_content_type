"""Drop the former one-question-per-slide constraint during module upgrade."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "ALTER TABLE slide_slide_essay "
        "DROP CONSTRAINT IF EXISTS slide_slide_essay_slide_unique"
    )
