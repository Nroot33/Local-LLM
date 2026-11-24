"""Windows에서 g2pkk가 요구하는 형태소 분석기 호환 계층."""

from kiwipiepy import Kiwi


class Mecab:
    def __init__(self):
        self._kiwi = Kiwi()

    def pos(self, text):
        return [(token.form, token.tag) for token in self._kiwi.tokenize(text)]
