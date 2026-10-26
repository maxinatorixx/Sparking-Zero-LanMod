"""Bounded admission diagnostics use the real matcher, without game calls."""
import copy
import json
from types import SimpleNamespace
import unittest

from native_sessions import NativeSessionDirectory, native_numeric_decision, native_numeric_matches
from szero_lan import GameServer
from test_native_sessions_v2 import A, B, C, create, data, member, predicate, query, request


class NativeDiagnosticsTests(unittest.TestCase):
    @staticmethod
    def original_numeric_matches(q, candidate, default=False):
        # Independent pre-diagnostic predicate, retained as a differential oracle.
        left, right = q["compatibility"], candidate["compatibility"]
        normalize = default if q["field_4e"] == 255 else q["field_4e"] != 0
        if left and right:
            if normalize:
                left, right = ((left - 1) & 0xffffffff) % 1000, ((right - 1) & 0xffffffff) % 1000
            if left != right:
                return False
        def predicate_result(item):
            key = int(item["key"])
            if key >= len(candidate["numeric"]):
                return None
            a, b = candidate["numeric"][key], item["value"]
            return (a == b, a < b, a <= b, a > b, a >= b)[item["comparison"]]
        return (not any(predicate_result(item) is False for item in q["filters"])
                and not any(predicate_result(pair["first"]) is False and predicate_result(pair["second"]) is False
                            for pair in q.get("compound_filters", [])))

    def capture_search(self, directory, owner=B, excluded=(), **fields):
        message = request("search", query=query(**fields), default_normalize=False,
                          materialization_profile=2, limit=1)
        with self.assertLogs("szero_lan", level="INFO") as captured:
            result = directory.handle(owner, message, excluded_sessions=excluded)
        line = next(line for line in captured.output if "Native candidates" in line)
        counts, details = line.split("counts=", 1)[1].split(" details=", 1)
        return result, json.loads(counts), json.loads(details), line

    def test_predicate_decisions_preserve_signed_missing_or_and_compatibility(self):
        candidate = data()
        cases = [query(), query(compatibility=2234), query(compatibility=2234, field_4e=1)]
        for comparison in range(5):
            for value in (-6, -5, -4):
                cases.append(query(filters=[predicate(0, comparison, value)]))
        for first, second in ((99, 0), (0, 99), (0, 1)):
            cases.append(query(compound_count=1, compound_filters=[{
                "first": predicate(first, 0, 99), "second": predicate(second, 0, 99)}]))
        for q in cases:
            reason, detail = native_numeric_decision(q, candidate, False)
            self.assertEqual(native_numeric_matches(q, candidate, False), reason is None)
            self.assertEqual(reason is None, self.original_numeric_matches(q, candidate))
            self.assertIsInstance(detail, dict)
        self.assertEqual(native_numeric_decision(query(compatibility=1), candidate, False)[0], "compatibility")
        self.assertEqual(native_numeric_decision(query(filters=[predicate(0, 0, 99)]), candidate, False)[0], "numeric")
        self.assertEqual(native_numeric_decision(cases[-1], candidate, False)[0], "compound")

    def test_first_exclusions_are_actual_filter_decisions(self):
        for reason in ("reserved", "version", "partition", "full", "flags", "profile", "own", "compatibility", "numeric", "compound"):
            with self.subTest(reason=reason):
                directory = NativeSessionDirectory()
                session = create(directory)
                stored = directory.sessions[session["session_id"]]
                fields, excluded, owner = {}, (), B
                if reason == "reserved": excluded = (stored.id,)
                elif reason == "version": stored.version = 1
                elif reason == "partition": stored.partition = ("f" * 64, 1, 0)
                elif reason == "full": stored.members[C] = "d" * 32
                elif reason == "flags": stored.create_flags = 5
                elif reason == "profile": stored.native_data = None
                elif reason == "own": owner = A
                elif reason == "compatibility": fields["compatibility"] = 1
                elif reason == "numeric": fields["filters"] = [predicate(0, 0, 99)]
                elif reason == "compound": fields.update(compound_count=1, compound_filters=[{
                    "first": predicate(0, 0, 99), "second": predicate(1, 0, 99)}])
                response, counts, details, _ = self.capture_search(directory, owner, excluded, **fields)
                self.assertEqual(response["sessions"], [])
                self.assertEqual(counts[reason], 1)
                self.assertEqual(sum(counts.values()), 1)
                self.assertEqual(details[0]["reason"], reason)

    def test_bounded_details_and_no_identity_address_or_stream_logging(self):
        directory = NativeSessionDirectory()
        for index in range(8):
            create(directory, owner=f"{index:032x}", label=f"private-identity-{index}")
        before = copy.deepcopy(directory.sessions)
        response, counts, details, line = self.capture_search(directory, filters=[predicate(0, 0, 99)])
        self.assertEqual(response["sessions"], [])
        self.assertEqual(counts["numeric"], 8)
        self.assertEqual(len(details), 4)
        self.assertEqual(directory.sessions, before)
        self.assertNotIn("identity", line)
        self.assertNotIn("127.0.0.1", line)
        self.assertNotIn(data()["stream"]["data_base64"], line)
        self.assertNotIn(member("private-identity-0")["identity_hex"][0], line)

    def test_acceptance_limit_and_wire_shape_unchanged(self):
        directory = NativeSessionDirectory()
        first = create(directory)
        create(directory, C, "c")
        response, counts, details, line = self.capture_search(directory)
        self.assertEqual(response["sessions"], [first])
        # Eligibility is evaluated before the final limit so an Elo-rejected
        # first candidate cannot hide a later eligible player. The diagnostics
        # describe native eligibility; the wire still contains only one room.
        self.assertEqual(counts["accepted"], 2)
        self.assertEqual(len(details), 2)
        self.assertIn("total=2 scanned=2 results=2", line)
        self.assertEqual(set(response), {"event", "version", "request_id", "op", "numeric_filter_only", "sessions"})

    def test_server_search_and_transaction_action_correlation(self):
        server = GameServer("127.0.0.1", 0)
        sent = []
        server.send = lambda peer, value: sent.append(value)
        server.notify_native_sessions = lambda owners: None
        server.notify_native_transport = lambda owners: None
        peer = SimpleNamespace(id=A, lobby=None, match=None)
        native = data()
        payload = request("create", native_data=native,
                          attributes={str(i): value for i, value in enumerate(native["numeric"])})
        with self.assertLogs("szero_lan", level="INFO") as captured:
            server.native_transaction_request(peer, {"op": "native_session_transaction", "request": {
                "version": 1, "op": "prepare", "transaction_id": "rpc-1", "request": payload}})
            sid = sent[-1]["session"]["session_id"]
            server.native_transaction_request(peer, {"op": "native_session_transaction", "request": {
                "version": 1, "op": "commit", "transaction_id": "rpc-1"}})
            server.native_request(SimpleNamespace(id=B, lobby=None, match=None), {
                "op": "native_session", "request": request("search", query=query(), default_normalize=False,
                    materialization_profile=2, limit=1)})
        lines = "\n".join(captured.output)
        self.assertIn(f"transaction=rpc-1 action=create session={sid} members=1 flags=0", lines)
        self.assertIn("results=1", lines)
        self.assertNotIn("identity_hex", lines)

    def test_match_logs_actual_admission_and_does_not_merge_incompatible_sessions(self):
        directory = NativeSessionDirectory()
        host = create(directory)
        guest_data = data("b")
        message = request("match", native_data=guest_data, attributes={"0": -5, "1": 8},
                          query=query(), default_normalize=False, create_flags=0)
        with self.assertLogs("szero_lan", level="INFO") as captured:
            joined = directory.handle(B, message)
        self.assertEqual(joined["action"], "join")
        self.assertEqual(joined["session"]["session_id"], host["session_id"])
        self.assertIn('"accepted":1', captured.output[0])
        self.assertEqual(len(directory.sessions), 1)
        directory = NativeSessionDirectory()
        host = create(directory)
        message["query"] = query(compatibility=1)
        with self.assertLogs("szero_lan", level="INFO") as captured:
            created = directory.handle(B, message)
        self.assertEqual(created["action"], "create")
        self.assertNotEqual(created["session"]["session_id"], host["session_id"])
        self.assertIn('"compatibility":1', captured.output[0])
        self.assertEqual(len(directory.sessions), 2)


if __name__ == "__main__":
    unittest.main()
