import unittest

from backend_services import LanBackendServices, MAX_PEERS, VIRTUAL_BASE


class BackendServicesTests(unittest.TestCase):
    def setUp(self):
        self.service = LanBackendServices()
        self.peer = "1" * 32

    def login(self, peer=None, name="Player"):
        return self.service.request(peer or self.peer, name, "/user/login.php", {})

    def test_login_required_fields_and_native_boolean_contract(self):
        result = self.login()
        self.assertIs(type(result["res"]), int)
        self.assertEqual(result["res"], 0)
        self.assertTrue(result["session_code"].startswith("szlan-"))
        self.assertEqual(result["redirect_url"], VIRTUAL_BASE)
        self.assertEqual(result["cdn_base_url"], VIRTUAL_BASE)
        self.assertIs(result["is_relogin"], False)
        self.assertIs(result["is_new"], False)
        self.assertEqual(result["match_completion_rate"], 100)
        for value in result["post_and_report_penalty_status"].values():
            self.assertEqual(value, {"penalty_level": 0, "is_penalty_period": False})

    def test_socket_ownership_distinct_sessions_and_disconnect(self):
        first = self.login()
        self.assertEqual(first, self.login())
        other = self.login("2" * 32)
        self.assertNotEqual(first["session_code"], other["session_code"])
        self.service.disconnect(self.peer)
        self.assertNotEqual(first["session_code"], self.login()["session_code"])
        self.service.disconnect(self.peer)
        self.service.disconnect(self.peer)
        self.assertEqual(other, self.login("2" * 32))

    def test_returned_records_do_not_mutate_owned_state(self):
        first = self.login()
        token = first["session_code"]
        first["session_code"] = "changed"
        first["player_card"]["match_result_list"].append({"x": 1})
        first["post_and_report_penalty_status"]["post_penalty_status"]["is_penalty_period"] = True
        second = self.login()
        self.assertEqual(second["session_code"], token)
        self.assertEqual(second["player_card"]["match_result_list"], [])
        self.assertIs(second["post_and_report_penalty_status"]["post_penalty_status"]
                      ["is_penalty_period"], False)

    def test_known_empty_transaction_and_optional_notice_contracts(self):
        self.login()
        self.assertEqual(self.service.request(self.peer, "Player", "/user/check_transaction.php", {}),
                         {"res": 0, "reward_ids": [], "match_phase": 0, "is_present_receive": False})
        self.assertEqual(self.service.request(self.peer, "Player", "/system/get_notice.php", {}), {"res": 0})

    def test_followups_require_same_live_connection_identity(self):
        with self.assertRaises(ValueError):
            self.service.request(self.peer, "Player", "/system/get_notice.php", {})
        self.login()
        with self.assertRaises(ValueError):
            self.service.request(self.peer, "Other", "/system/get_notice.php", {})
        with self.assertRaises(ValueError):
            self.login(name="Other")
        self.service.disconnect(self.peer)
        with self.assertRaises(ValueError):
            self.service.request(self.peer, "Player", "/system/get_notice.php", {})

    def test_exact_report_counts_and_empty_banner_native_contract(self):
        self.login()
        self.assertEqual(self.service.request(self.peer, "Player", "/pvp/get_report_taken_counts.php", {}),
                         {"res": 0, "rank_match_remove_fight_report_taken_count": 0,
                          "rank_match_report_inciting_report_taken_count": 0,
                          "rank_match_other_report_taken_count": 0,
                          "rank_match_invalid_settings_report_taken_count": 0})
        self.assertEqual(self.service.request(self.peer, "Player", "/shop_banner/get_list.php", {}),
                         {"res": 0, "shop_banner_info_list": []})

    def test_every_supported_success_has_required_common_result_field(self):
        for path in ("/user/login.php", "/user/check_transaction.php", "/system/get_notice.php",
                     "/pvp/get_report_taken_counts.php", "/shop_banner/get_list.php"):
            with self.subTest(path=path):
                response = self.service.request(self.peer, "Player", path, {})
                self.assertIs(type(response["res"]), int)
                self.assertEqual(response["res"], 0)
                self.assertNotIn("data", response)  # Route fields stay at the JSON root.

    def test_no_unknown_absolute_traversal_or_cross_player_route(self):
        for path in ("", "user/login.php", "https://szero.invalid/user/login.php",
                     "/../user/login.php", "/user/get_player_card.php", "/user/update_player_rank.php",
                     "/user/login.php?x=1", "/USER/login.php", None):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.service.request(self.peer, "Player", path, {})

    def test_bodies_including_credentials_and_target_ids_are_refused(self):
        for body in (None, [], "{}", {"auth_info": "secret"},
                     {"nested": {"auth_info": "secret"}}, {"peer_id": "2" * 32},
                     {"session_code": "official-token"}, {"platform_user_id": "1"}):
            with self.subTest(kind=type(body).__name__), self.assertRaises(ValueError):
                self.service.request(self.peer, "Player", "/user/login.php", body)
        self.assertEqual(self.service._sessions, {})

    def test_invalid_peer_and_name_are_failure_atomic(self):
        for peer in (None, "", "a" * 31, "A" * 32, "g" * 32):
            with self.assertRaises(ValueError):
                self.service.request(peer, "Player", "/user/login.php", {})
        for name in (None, "", " Player", "Player ", "a" * 49, "a\n", "a\x7f"):
            with self.assertRaises(ValueError):
                self.service.request(self.peer, name, "/user/login.php", {})
        self.assertEqual(self.service._sessions, {})

    def test_bounded_capacity_and_reuse_after_disconnect(self):
        for i in range(MAX_PEERS):
            self.login(f"{i:032x}")
        with self.assertRaises(ValueError):
            self.login("f" * 32)
        self.service.disconnect("0" * 32)
        self.assertTrue(self.login("f" * 32)["session_code"])

    def test_card_requires_login_and_exact_owned_target_resolution(self):
        seen = []
        def resolve(peer, target):
            seen.append((peer, target))
            if target != "self":
                raise ValueError("not a session participant")
            return {"display_name": "Vegeta"}
        self.service.card_resolver = resolve
        path = "/user/get_player_card.php"
        with self.assertRaises(ValueError):
            self.service.request(self.peer, "Player", path, {"target": "self"})
        self.login()
        card = self.service.request(self.peer, "Player", path, {"target": "self"})
        self.assertEqual(card["res"], 0)
        self.assertIs(type(card["player_card"]["player_rank"]), int)
        self.assertFalse(card["player_card"]["rank_match_hide_flag"])
        self.assertEqual(seen, [(self.peer, "self")])
        for body in ({}, {"target": "official-user"}, {"target": "self", "auth_info": "x"},
                     {"target": "szlan:"+"2"*32}):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.service.request(self.peer, "Player", path, body)

    def test_clean_lan_profile_passes_recovered_ranked_completion_filter(self):
        from native_sessions import native_numeric_decision
        completion = self.login()["match_completion_rate"]
        # Captured ranked rejection: key7 comparison2 query0 candidate80.
        # Original145a5d990: attr6=own completion, attr7=requested minimum.
        query = {"compatibility": 0, "filters": [
            {"key": "7", "comparison": 2, "value": completion},
            {"key": "6", "comparison": 4, "value": 80}],
            "compound_count": 0, "distance": 0,
            "field_4c": 0, "field_4d": 0, "field_4e": 255}
        candidate = {"compatibility": 0, "numeric": [0]*6+[100, 80]}
        self.assertEqual(native_numeric_decision(query, candidate, False), (None, {}))
        query["filters"][0]["value"] = 0
        self.assertEqual(native_numeric_decision(query, candidate, False)[0], "numeric")
        query["filters"][0]["value"] = completion
        candidate["numeric"][6] = 70
        self.assertEqual(native_numeric_decision(query, candidate, False)[0], "numeric")


if __name__ == "__main__":
    unittest.main()
