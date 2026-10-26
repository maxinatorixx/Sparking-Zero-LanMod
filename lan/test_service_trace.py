"""Real Win64 temporary function-wrapper fixture, not game execution."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

@unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine"),
                     "requires existing MinGW and disposable Wine")
class ServiceTraceTests(unittest.TestCase):
    def test_real_probe_forwarding_results_thread_scope_and_instruction_restore(self):
        native=Path(__file__).resolve().parent/"native"
        with tempfile.TemporaryDirectory(prefix="szero-service-probe-") as folder:
            exe=Path(folder)/"probe.exe"
            subprocess.run(["x86_64-w64-mingw32-gcc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                            "-municode","-static-libgcc","-Wl,--no-insert-timestamp",
                            str(native/"test_service_trace.c"),
                            *(str(native/"vendor/minhook/src"/name) for name in
                              ("buffer.c","hook.c","trampoline.c","hde/hde64.c")),
                            "-o",str(exe),"-lbcrypt"],
                           check=True,capture_output=True)
            prefix=os.environ.get("WINEPREFIX","")
            if not prefix.startswith("/tmp/szero-"):
                raise RuntimeError("Use a disposable /tmp/szero-* Wine prefix, never the game prefix")
            for mode in ("normal","deep","transport","battle_result","operational","postpair","postpairdeep","postpairlate","fiber","cap","stop"):
                ident=uuid.uuid4().hex
                result=subprocess.run(["wine",str(exe),ident,mode],capture_output=True,text=True,
                                      env=dict(os.environ,WINEDEBUG="-all"),timeout=30)
                log=Path(folder)/f"native_service_trace_{ident}.jsonl"
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr,log.read_text() if log.exists() else "no log"))
                records=[json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(records[0]["schema"],5)
                self.assertEqual(records[0]["probe_revision"], "postresult2")
                if mode=="operational":
                    self.assertIn("exclusive result setter ownership",result.stdout)
                    self.assertFalse(any(r['event'] in ('enter','return','native_battle_result') for r in records))
                    self.assertTrue(records[-1]['restored'])
                    continue
                if mode=="battle_result":
                    self.assertIn("read-only scope passed",result.stdout)
                    events=[r for r in records if r["event"]=="native_battle_result"]
                    self.assertEqual(len(events),11)
                    self.assertEqual([r["native_battle_result"] for r in events[:8]],list(range(8)))
                    self.assertEqual([r["native_battle_result_name"] for r in events[:8]],
                        ["None","Win","Lose","Draw","Timeup","RingOut","Win1P","Win2P"])
                    self.assertEqual([r["native_battle_result_valid"] for r in events],[True]*8+[False]*3)
                    self.assertEqual([r["readable"] for r in events],[True]*9+[False]*2)
                    self.assertTrue(all(r["boundary"]=="set_battle_result" and not r["code_valid"] and r["code"]==0 for r in events))
                    self.assertTrue(records[-1]["restored"])
                    self.assertEqual(records[-1]["inflight"],0)
                    self.assertNotIn("abcdef01",log.read_text().lower())
                    continue
                if mode in ("postpairdeep", "postpairlate"):
                    returned=[r for r in records if r["event"]=="return"]
                    self.assertEqual([r["boundary"] for r in returned],
                        ["post_pair_member", "post_pair_wait", "post_pair_wait_result", "post_pair_peer_start",
                         "post_pair_commit", "post_pair_connect", "post_pair_prepare"])
                    self.assertEqual([r["code_valid"] for r in returned], [False,False,True,True,True,True,True])
                    self.assertEqual([r["tag"] for r in returned[:2]], [2,2])
                    self.assertEqual([r["code"] for r in returned[2:]], [0x90,0x57c3a7bb,0x800fa,0x800fa,0x37980004])
                    self.assertTrue(all(r["candidate_parent"]==1 for r in returned[:5]))
                    self.assertEqual(returned[5]["candidate_parent"],0)
                    self.assertTrue(records[-1]["restored"])
                    self.assertTrue(records[-1]["post_pair_extension_used"])
                    self.assertEqual(records[0]["max_duration_ms"],records[0]["pair_wait_ms"]+records[0]["duration_ms"])
                    self.assertEqual(records[-1]["reason"],"capture_timeout")
                    if mode=="postpairlate":
                        self.assertTrue(any(r["event"]=="waiting_for_pair" for r in records))
                        self.assertTrue(any(r["event"]=="pair_capture_started" for r in records))
                        self.assertFalse(any(r.get("boundary")=="online_check" for r in records))
                    self.assertNotIn("deadbeef", log.read_text().lower())
                    continue
                if mode=="postpair":
                    returned=[r for r in records if r["event"]=="return"]
                    self.assertEqual([r["boundary"] for r in returned], ["post_pair_connect", "post_pair_prepare"])
                    self.assertEqual([r["code"] for r in returned], [0x800fa,0x37980004])
                    self.assertTrue(all(r["code_valid"] for r in returned))
                    self.assertTrue(records[-1]["restored"])
                    continue
                if mode=="transport":
                    self.assertIn("transport origin classification and forwarding passed",result.stdout)
                    returned=[r for r in records if r["event"]=="return"]
                    self.assertEqual([r["boundary"] for r in returned[:3]],
                                     ["http_failure_marker","http_error_copy","steam_http_exchange"])
                    self.assertEqual([r["failure_origin"] for r in returned[:3]],["create_request","send_request","none"])
                    self.assertFalse(returned[0]["code_valid"])
                    self.assertEqual(returned[1]["code"],0x57c80000)
                    self.assertEqual(returned[2]["tag"],1)
                    self.assertEqual(returned[2]["code"],0x57c80000)
                    self.assertEqual([r["backend_status_valid"] for r in returned[3:]],[True,True,False])
                    self.assertEqual([r["backend_status"] for r in returned[3:]],[0x80088,0x57c80000,0])
                    self.assertTrue(records[-1]["restored"])
                    continue
                if mode=="deep":
                    self.assertIn("identical outer errors distinguished",result.stdout)
                    returned=[r for r in records if r["event"]=="return"]
                    self.assertEqual([r["boundary"] for r in returned],
                                     ["login_provider","service_login","login_provider",
                                      "login_response","backend_login","service_login"])
                    self.assertEqual([r["code"] for r in returned if r["boundary"]=="service_login"],
                                     [0x57c80000,0x57c80000])
                    self.assertEqual([r["code_valid"] for r in returned if r["boundary"]=="login_provider"],[True,False])
                    self.assertTrue(records[-1]["restored"])
                    self.assertNotIn("deadbeef",log.read_text().lower())
                    continue
                if mode=="fiber":
                    self.assertIn("resumed unchanged",result.stdout)
                    self.assertEqual(records[-1]["inflight"],1)
                    self.assertTrue(records[-1]["restored"])
                    self.assertEqual(len([r for r in records if r["event"] in ("enter","return")]),3)
                    continue
                if mode=="cap":
                    self.assertIn("preserved all calls",result.stdout)
                    self.assertEqual(len([r for r in records if r["event"] in ("enter","return")]),512)
                    self.assertTrue(records[-1]["restored"])
                    continue
                self.assertIn("contracts passed",result.stdout)
                returned=[r for r in records if r["event"]=="return"]
                self.assertEqual(len(returned),16)
                self.assertEqual([r["mask"] for r in returned if r["boundary"]=="online_check"],[32,4,8])
                for r in returned:
                    self.assertTrue(r["readable"])
                    if r["boundary"]=="login_provider":
                        self.assertIn(r["tag"],(1,2))
                        self.assertEqual(r["code_valid"],r["tag"]==1)
                        self.assertEqual(r["code"],0x57c80000 if r["tag"]==1 else 0)
                        continue
                    self.assertTrue(r["code_valid"])
                    self.assertEqual(r["code"],0x90 if r["boundary"]=="platform_check" else 0x57c80000)
                    self.assertEqual(r["tag"],2 if r["boundary"]=="platform_check" else 0)
                self.assertEqual([r["category"] for r in records if r["event"]=="enter" and r["boundary"]=="maintenance"],[2,2,2])
                self.assertEqual(records[-1]["event"],"stopped")
                self.assertTrue(records[-1]["restored"])
                self.assertEqual(records[-1]["inflight"],0)
                if mode=="stop":
                    self.assertEqual(records[-1]["reason"],"bridge_stopped")
                    self.assertTrue(any(r["event"]=="waiting_for_pair" for r in records))
                else:
                    self.assertEqual(records[-1]["reason"],"pair_wait_timeout")
                self.assertIn("current game thread only",records[0]["coverage"])
                self.assertEqual(len([r for r in returned if r["boundary"]=="backend_login"]),1)
                self.assertEqual(len([r for r in returned if r["boundary"]=="login_response"]),1)
                self.assertNotIn("deadbeef",log.read_text().lower())
            # The ACTUAL production DLL must refuse this unknown executable,
            # never treating the test-only native export table as authorization.
            dll=Path(folder)/"service_trace.dll"
            sources=[native/"service_trace.c",*(native/"vendor/minhook/src"/name for name in
                       ("buffer.c","hook.c","trampoline.c","hde/hde64.c"))]
            subprocess.run(["x86_64-w64-mingw32-gcc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                            "-shared","-static-libgcc",*(str(p) for p in sources),"-o",str(dll),"-lbcrypt"],
                           check=True,capture_output=True)
            ident=uuid.uuid4().hex
            windows_dll="Z:"+str(dll).replace("/","\\")
            quiet_ident=uuid.uuid4().hex
            quiet=subprocess.run(["wine",str(exe),quiet_ident,"quietproduction",windows_dll],capture_output=True,text=True,
                                 env=dict(os.environ,WINEDEBUG="-all"),timeout=30)
            self.assertEqual(quiet.returncode,0,quiet.stdout+quiet.stderr)
            self.assertFalse((Path(folder)/f"native_service_trace_{quiet_ident}.jsonl").exists())
            result=subprocess.run(["wine",str(exe),ident,"production",windows_dll],capture_output=True,text=True,
                                  env=dict(os.environ,WINEDEBUG="-all"),timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            records=[json.loads(line) for line in (Path(folder)/f"native_service_trace_{ident}.jsonl").read_text().splitlines()]
            self.assertEqual(records,[{"event":"refused","reason":"unsupported_image_or_modified_probe_bytes"}])

if __name__=="__main__":
    unittest.main()
