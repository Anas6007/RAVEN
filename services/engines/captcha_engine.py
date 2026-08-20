import random


class CaptchaEngine:

    @staticmethod
    def generate():

        operation = random.choice(["+", "-", "*"])

        if operation == "+":

            a = random.randint(1, 20)
            b = random.randint(1, 20)
            answer = a + b

        elif operation == "-":

            a = random.randint(10, 30)
            b = random.randint(1, a)
            answer = a - b

        else:

            a = random.randint(2, 10)
            b = random.randint(2, 10)
            answer = a * b

        question = f"{a} {operation} {b}"

        return question, answer

    @staticmethod
    def check(answer, user_answer):

        try:
            return int(user_answer) == int(answer)

        except Exception:
            return False