import unittest
from elo_matchmaking import EloMatchmaking,validate_config,DEFAULTS


class EloMatchmakingTests(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.match=EloMatchmaking(clock=lambda:self.now)

    def pair(self,gap,wait):
        self.match.observe('host','single',1000)
        self.now=wait
        self.match.observe('guest','single',1000+gap)
        return self.match.rank_candidates('guest',[('host','single',1000)])

    def test_exact_expansion_boundaries_and_longer_wait(self):
        for seconds,window in ((0,100),(14.999,100),(15,200),(74.999,500),(75,600),(119.999,600),(120,None)):
            self.assertEqual(self.match.window(seconds),window)
        self.assertEqual(self.pair(200,15),['host'])
        self.setUp();self.assertEqual(self.pair(201,15),[])
        self.setUp();self.assertEqual(self.pair(600,75),['host'])
        self.setUp();self.assertEqual(self.pair(601,75),[])
        self.setUp();self.assertEqual(self.pair(200000,120),['host'])

    def test_repeat_search_or_host_advertisement_preserves_start(self):
        self.match.observe('host','single',1000)
        self.now=15;self.match.observe('host','single',1001)
        self.assertEqual(self.match.queue['host'].started,0)
        self.match.observe('new','single',1201)
        self.assertEqual(self.match.rank_candidates('new',[('host','single',1001)]),['host'])

    def test_longest_wait_then_closest_and_stable_tie(self):
        self.match.observe('old','single',1100)
        self.now=1;self.match.observe('near','single',1001)
        self.now=2;self.match.observe('searcher','single',1000)
        values=[('near','single',1001),('old','single',1100)]
        self.assertEqual(self.match.rank_candidates('searcher',values),['old','near'])
        # When searcher is oldest, both pairs share that same maximum wait.
        self.match=EloMatchmaking(clock=lambda:self.now);self.match.observe('searcher','single',1000)
        self.now=3
        for who,rating in (('far',1100),('near',1001),('tie',1001)):self.match.observe(who,'single',rating)
        self.assertEqual(self.match.rank_candidates('searcher',[('far','single',1100),('tie','single',1001),('near','single',1001)]),['near','tie','far'])

    def test_cancel_leave_or_mode_change_resets_and_stale_is_not_recreated(self):
        self.match.observe('host','single',1000);self.now=100
        self.match.cancel('host');self.match.observe('host','single',1000)
        self.assertEqual(self.match.queue['host'].started,100)
        self.now=110;self.match.observe('host','team',1000)
        self.assertEqual(self.match.queue['host'].started,110)
        self.match.observe('guest','team',1000)
        self.now=710
        self.assertEqual(self.match.rank_candidates('guest',[('host','team',1000)]),[])
        self.assertNotIn('host',self.match.queue)

    def test_never_cross_modes_or_add_nonqueued_or_native_filtered_candidates(self):
        self.match.observe('a','single',1000);self.match.observe('b','dp',1000)
        self.match.observe('c','single',1000)
        self.now=120
        self.assertEqual(self.match.rank_candidates('a',[('b','dp',1000),('missing','single',1000)]),[])
        self.assertEqual(self.match.rank_candidates('a',[]),[])
        self.assertEqual(self.match.rank_candidates('a',[('c','single',1000)]),['c'])

    def test_validation_rejects_bools_unknown_ranges_and_bad_clock(self):
        for field in DEFAULTS:
            if field=='enabled':continue
            with self.subTest(field=field),self.assertRaises(ValueError):validate_config({field:True})
        for value in ({'enabled':1},{'unknown':0},{'initial_range':200,'maximum_range':100},
                      {'range_step':0},{'expand_interval_seconds':0},
                      {'queue_ttl_seconds':119}):
            with self.assertRaises(ValueError):validate_config(value)
        with self.assertRaises(ValueError):self.match.observe('a','single',True)
        with self.assertRaises(ValueError):EloMatchmaking(clock=lambda:float('nan')).observe('a','single',1000)

    def test_disabled_policy_still_keeps_verified_mode_and_queue_boundaries(self):
        match=EloMatchmaking({'enabled':False},clock=lambda:self.now)
        match.observe('a','single',1000);match.observe('b','single',5000)
        self.assertEqual(match.rank_candidates('a',[('b','single',5000)]),['b'])


class RankedDirectoryPolicyTests(unittest.TestCase):
    def setUp(self):
        import test_native_sessions_v2 as f
        from native_sessions import NativeSessionDirectory
        from elo_matchmaking import RankedSessionPolicy
        self.f=f;self.now=0
        self.profiles={f.A:{'ranks':[{'mode':'single','rating':1000},{'mode':'dp','rating':1000}]},
                       f.B:{'ranks':[{'mode':'single','rating':1201},{'mode':'dp','rating':1201}]},
                       f.C:{'ranks':[{'mode':'single','rating':1001},{'mode':'dp','rating':1001}]}}
        self.policy=RankedSessionPolicy(lambda owner:self.profiles.get(owner),lambda:True,clock=lambda:self.now)
        self.directory=NativeSessionDirectory(candidate_policy=self.policy)

    def create(self,owner,compat=20002):
        return self.f.create(self.directory,owner,owner[0],dict(self.f.data(owner[0]),compatibility=compat))

    def search(self,owner,compat=20002,**extra):
        return self.f.search(self.directory,owner,compatibility=compat,**extra)

    def test_native_filters_before_elo_and_expands_without_real_wait(self):
        room=self.create(self.f.A)
        self.assertEqual(self.search(self.f.B),[])
        self.now=15;self.assertEqual(self.search(self.f.B),[])
        self.now=30;self.assertEqual(self.search(self.f.B),[room])
        self.now=120
        # Even unrestricted Elo never overrides a native numeric rejection.
        self.assertEqual(self.search(self.f.B,filters=[self.f.predicate(value=9000)]),[])
        self.assertEqual(self.search(self.f.B,compat=20003),[])

    def test_sort_before_one_result_limit_and_preserve_casual_order(self):
        distant=self.create(self.f.A)
        close=self.create(self.f.C)
        self.assertEqual(self.search(self.f.B),[])  # gaps201/200 exceed initial100
        self.now=15
        self.assertEqual(self.search(self.f.B),[close])  # one result AFTER Elo
        self.directory.handle(self.f.A,self.f.request('leave'))
        self.directory.handle(self.f.C,self.f.request('leave'))
        casual_a=self.create(self.f.A,20004);self.create(self.f.C,20004)
        self.assertEqual(self.search(self.f.B,20004),[casual_a])

    def test_guest_refusal_retry_timestamps_cancel_and_transaction_copy(self):
        import copy
        room=self.create(self.f.A)
        copied=copy.deepcopy(self.directory)
        self.assertIs(copied.candidate_policy,self.policy)
        self.now=20;self.search(self.f.B)
        self.assertEqual(self.policy.match.queue[self.f.B].started,20)
        self.now=30;self.search(self.f.B)
        self.assertEqual(self.policy.match.queue[self.f.B].started,20)
        self.policy.cancel(self.f.B);self.now=50;self.search(self.f.B)
        self.assertEqual(self.policy.match.queue[self.f.B].started,50)
        self.profiles.pop(self.f.B);self.policy.invalidate_ratings()
        self.assertEqual(self.search(self.f.B),[])
        self.policy.cancel(self.f.A);self.now=120
        self.assertEqual(self.search(self.f.C),[])  # cancelled live host cannot be resurrected by a search
        self.directory.handle(self.f.A,self.f.request('leave'))
        self.assertNotIn(self.f.A,self.policy.match.queue)

    def test_verified_compatibility_namespace_mapping(self):
        from elo_matchmaking import ranked_session_mode
        for ns in (0,1000,20000,90000):
            self.assertEqual(ranked_session_mode(ns+2),'single')
            self.assertEqual(ranked_session_mode(ns+3),'dp')
            for kind in (1,4,5,6,7,8):self.assertIsNone(ranked_session_mode(ns+kind))
        for value in (0,True,-1,2**32,'20002'):self.assertIsNone(ranked_session_mode(value))
