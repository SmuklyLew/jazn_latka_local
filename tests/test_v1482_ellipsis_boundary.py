from latka_jazn.nlp.ellipsis_resolver import EllipsisResolver


def test_v1482_poki_co_not_ellipsis():
    r = EllipsisResolver().resolve('póki co. Czy teraz rozmawiam z Jaźnią Łatki?', previous_text='coś o runtime')
    assert not r.is_elliptic


def test_v1482_i_co_dalej_can_be_continuation():
    r = EllipsisResolver().resolve('I co dalej?', previous_text='napraw system Jaźni')
    assert r.is_elliptic


def test_v1482_runtime_question_blocks_false_continuation():
    r = EllipsisResolver().resolve('I co teraz z runtime-preview i --chat?', previous_text='napraw system')
    assert not r.is_elliptic
