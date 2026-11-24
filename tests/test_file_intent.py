import unittest

from local_agent import is_file_creation_request


class FileIntentTests(unittest.TestCase):
    def test_topic_contains_method(self):
        self.assertTrue(is_file_creation_request("고전 소설의 이야기 전개 방법과 그에 대한 설명을 txt 문서로 바탕화면에 하나 작성해 줘"))

    def test_explicit_mixed_slash_path(self):
        self.assertTrue(is_file_creation_request(r"C:\Users\PC\Desktop/고전소설_이야기전개.txt 해당위치에 txt 문서로 작성해 줘"))

    def test_question_about_file_creation(self):
        self.assertFalse(is_file_creation_request("TXT 파일을 만드는 방법 알려줘"))


if __name__ == "__main__":
    unittest.main()
