import unicodedata
import unittest

from backend.arena import Arena, ArenaError
from backend.nickname_policy import POLICY, nickname_error, normalize_nickname, safe_nickname, validate_nickname


class NicknamePolicyTests(unittest.TestCase):
    def test_vietnamese_names_remain_valid(self):
        names = ['Nguyễn Phúc Long', 'Đức Dũng', 'Bùi Quốc Cường', 'Cúc', 'Dung', 'Đăng',
                 'Du', 'Di', 'Dư', 'Các Bạn', 'Lớn', 'Lợn', 'Chim Cút', 'Bướm', 'Đèo Xanh',
                 'Dẻo Thơm', 'Lồng Đèn', 'Đĩa Xinh', 'Đụng Tay', 'Đụn Rơm',
                 'Sóc_5A', 'Bạn-123456', 'Khối 5', 'Chim Cut']
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(nickname_error(name), '')
                self.assertEqual(safe_nickname(name), name)
        self.assertEqual(validate_nickname('  Nguyễn   Phúc Long  '), 'Nguyễn Phúc Long')
        self.assertEqual(validate_nickname(unicodedata.normalize('NFD', 'Đức Dũng')), 'Đức Dũng')
        self.assertEqual(normalize_nickname('Sóc１２'), 'Sóc12')

    def test_inappropriate_words_case_accent_separation_and_leet(self):
        names = ['ĐỊT', 'đụ', 'đĩ', 'lồn', 'cặc', 'buồi', 'cứt', 'đéo', 'đụ1', 'l_ồ_n',
                 'đ_ụ', 'D C M', 'd-c-m', 'đ ị t', 'D1T M3', 'ditme', 'du_ma', 'con cac',
                 'cailon', 'an-cut', 'đồ ngu', 'khốn nạn', 'VCL', 'FUCK', 'sh1t', 'bitch',
                 'địtcon', 'cặccon', 'cứtcon', 'lồncon', 'đụcon']
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(nickname_error(name), POLICY['messages']['inappropriate'])
                self.assertEqual(safe_nickname(name), POLICY['fallback'])

    def test_phone_numbers_and_mixed_number_words_are_private(self):
        names = ['0912345678', '+84 912 345 678', '0084-912-345-678', 'Linh 0912345678',
                 '09.12.34.56.78', '０９１２３４５６７８', '٠٩١٢٣٤٥٦٧٨', 'Linh 123 4567',
                 'không chín một hai ba bốn năm', 'khong chin 1 hai 3 bon 5',
                 'Linh0chin1hai3bon5', '123456']
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(nickname_error(name), POLICY['messages']['phone'])
                self.assertEqual(safe_nickname(name), POLICY['fallback'])

    def test_format_blocks_contact_markup_and_invisible_characters(self):
        names = [None, 123, [], '', 'A', 'A'*41, '１２', 'abc@example.com', '<img src=x>',
                 'Bạn\u200bhọc', 'Bạn\nHọc', 'Bạn\tHọc', 'Bạn\u202ehọc', 'Bạn😀', '___']
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(nickname_error(name))
                self.assertEqual(safe_nickname(name), POLICY['fallback'])
                with self.assertRaises(ValueError):
                    validate_nickname(name)

    def test_direct_arena_validation_and_legacy_room_names(self):
        arena = Arena()
        with self.assertRaises(ArenaError):
            arena.handle({'action': 'create', 'name': '0912345678', 'grade': 5})
        with self.assertRaises(ArenaError):
            arena.handle({'action': 'create', 'name': 'dcm', 'grade': 5})
        owner = arena.handle({'action': 'create', 'name': 'Minh Anh', 'grade': 5, 'public': True})
        room = arena.rooms[owner['code']]
        room['players'][owner['token']]['name'] = '0912345678'
        self.assertEqual(arena.handle({'action': 'list', 'grade': 5, 'accountId': 'other'})['rooms'][0]['name'], 'Bạn học')
        self.assertEqual(arena.handle({'action': 'state', **owner})['players'], ['Bạn học'])
        friend = arena.handle({'action': 'join', 'name': 'Gia Huy', 'grade': 5, 'code': owner['code']})
        self.assertEqual(arena.handle({'action': 'state', **friend})['opponent'], 'Bạn học')
        arena.handle({'action': 'accept', **owner})
        room['readyAt'] = 0
        self.assertEqual(arena.handle({'action': 'state', **friend})['battle']['opponent'], 'Bạn học')


if __name__ == '__main__':
    unittest.main()
