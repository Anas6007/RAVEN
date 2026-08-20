"""
اختبار CaptchaEngine.
"""

from services.engines.captcha_engine import CaptchaEngine


def test_generate():
    question, answer = CaptchaEngine.generate()
    assert isinstance(question, str)
    assert isinstance(answer, int)
    print(f"✅ السؤال: {question} = {answer}")


def test_check_correct():
    _, answer = CaptchaEngine.generate()
    assert CaptchaEngine.check(answer, str(answer)) is True
    print("✅ إجابة صحيحة تمر.")


def test_check_wrong():
    _, answer = CaptchaEngine.generate()
    assert CaptchaEngine.check(answer, str(answer + 1)) is False
    print("✅ إجابة خاطئة مرفوضة.")


if __name__ == "__main__":
    test_generate()
    test_check_correct()
    test_check_wrong()
    print("\n✅ جميع الاختبارات نجحت.")
