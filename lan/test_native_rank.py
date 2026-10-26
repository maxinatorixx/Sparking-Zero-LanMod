"""Typed own-rank echo validation; these values never authorize persistent Elo."""
import copy
import json
import math
import struct
import unittest

from native_rank import validate_rank_snapshot


def snapshot(**updates):
    return dict({'rank_title':'Rank 星 A','rank_point':3456,'prev_need_point':3000,
        'next_need_point':4000,'win_streak':9,'win_streak_r_bits':0x3fa00000,
        'app_multiplayer_mode':2,'battle_type':1,'pvp_extra_type':0,
        'rank_range':3,'rank':7},**updates)


class NativeRankTests(unittest.TestCase):
    def test_nonzero_native_fields_are_preserved_in_fresh_converted_snapshot(self):
        original=snapshot();before=copy.deepcopy(original)
        value=validate_rank_snapshot(original)
        self.assertEqual(value['rank_title'],'Rank 星 A')
        self.assertEqual(value['rank_point'],3456)
        self.assertEqual(value['rank'],7)
        self.assertEqual(value['win_streak'],9)
        self.assertEqual(value['win_streak_r'],1.25)
        self.assertIs(type(value['win_streak_r']),float)
        self.assertEqual(set(value),(set(original)-{'win_streak_r_bits'})|{'win_streak_r'})
        self.assertEqual(original,before)
        value['rank_point']=0
        self.assertEqual(original,before)

    def test_exact_field_set_rejects_missing_extra_or_other_player_authority(self):
        for invalid in (None,[],0,snapshot(account_id=9),snapshot(player_id='peer'),
                        snapshot(outcome=1),snapshot(rank_match_info={}),snapshot(win_streak_r=1.25)):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                validate_rank_snapshot(invalid)
        for field in snapshot():
            invalid=snapshot();invalid.pop(field)
            with self.subTest(missing=field),self.assertRaises(ValueError):
                validate_rank_snapshot(invalid)

    def test_title_uses_utf8_byte_bound_and_rejects_nul_controls_surrogates(self):
        for title in ('','x'*128,'星'*42,'😀'*32):
            self.assertEqual(validate_rank_snapshot(snapshot(rank_title=title))['rank_title'],title)
        for title in ('x'*129,'星'*43,'😀'*33,'line\nfeed','tab\tstop','nul\0stop',
                      'delete\x7f','control\u0085','bad\ud800',None,12):
            with self.subTest(title=repr(title)),self.assertRaises(ValueError):
                validate_rank_snapshot(snapshot(rank_title=title))

    def test_signed_point_bounds_preserve_negative_native_sentinels(self):
        for field in ('rank_point','prev_need_point','next_need_point'):
            for value in (-(2**31),-1,0,2**31-1):
                self.assertEqual(validate_rank_snapshot(snapshot(**{field:value}))[field],value)
            for value in (-(2**31)-1,2**31,True,1.0,'1',None):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    validate_rank_snapshot(snapshot(**{field:value}))

    def test_unsigned_count_and_bits_bounds_are_exact_integer_types(self):
        for value in (0,2**32-1):
            self.assertEqual(validate_rank_snapshot(snapshot(win_streak=value))['win_streak'],value)
        for field in ('win_streak','win_streak_r_bits'):
            for value in (-1,2**32,True,1.0,'1',None):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    validate_rank_snapshot(snapshot(**{field:value}))

    def test_float_bits_reject_every_nonfinite_family(self):
        for bits in (0x7f800000,0xff800000,0x7fc00000,0x7f800001,0xffc00001,0xffffffff):
            with self.subTest(bits=hex(bits)),self.assertRaises(ValueError):
                validate_rank_snapshot(snapshot(win_streak_r_bits=bits))

    def test_finite_float32_bits_survive_json_without_locale_dependent_text(self):
        for bits in (0,0x80000000,1,0x80000001,0x3e99999a,0x3fa00000,0xbf800000,0x7f7fffff):
            value=validate_rank_snapshot(snapshot(win_streak_r_bits=bits))['win_streak_r']
            self.assertTrue(math.isfinite(value))
            encoded=json.dumps({'value':value},allow_nan=False)
            restored=json.loads(encoded)['value']
            self.assertEqual(struct.unpack('<I',struct.pack('<f',restored))[0],bits)
        self.assertEqual(math.copysign(1,validate_rank_snapshot(snapshot(win_streak_r_bits=0x80000000))['win_streak_r']),-1)

    def test_mode_fields_are_uint8_without_unverified_enum_remapping(self):
        for field in ('app_multiplayer_mode','battle_type','pvp_extra_type'):
            for value in (0,255):
                self.assertEqual(validate_rank_snapshot(snapshot(**{field:value}))[field],value)
            for value in (-1,256,True,1.0,'1'):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    validate_rank_snapshot(snapshot(**{field:value}))

    def test_rank_fields_are_signed_bytes_without_mapping_elo_to_native_rank(self):
        for field in ('rank_range','rank'):
            for value in (-128,-1,0,127):
                self.assertEqual(validate_rank_snapshot(snapshot(**{field:value}))[field],value)
            for value in (-129,128,1000,True,1.0,'1'):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    validate_rank_snapshot(snapshot(**{field:value}))


if __name__=='__main__':unittest.main()
