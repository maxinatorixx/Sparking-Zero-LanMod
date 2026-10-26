"""Server policy for an explicitly verified Ranked queue, never native eligibility.

Callers must first enforce all native settings/room predicates and establish
Ranked mode and account ownership from their trusted connection context. No
opaque native numeric slot is interpreted here. This module cannot admit a
candidate the original native predicate rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import logging
import time

DEFAULTS={
    'enabled': True,
    'initial_range': 100,
    'range_step': 100,
    'expand_interval_seconds': 15,
    'maximum_range': 600,
    'any_rating_after_seconds': 120,
    'queue_ttl_seconds': 600,
}
MODES=frozenset(('single','dp','team'))


def validate_config(value=None):
    if value is None:
        value={}
    if type(value) is not dict or not set(value)<=set(DEFAULTS):
        raise ValueError('invalid elo_matchmaking settings')
    result=dict(DEFAULTS,**value)
    if type(result['enabled']) is not bool:
        raise ValueError('elo_matchmaking.enabled must be boolean')
    bounds={'initial_range':(0,100000),'range_step':(1,100000),
            'expand_interval_seconds':(1,3600),'maximum_range':(0,100000),
            'any_rating_after_seconds':(1,86400),'queue_ttl_seconds':(1,86400)}
    for key,(low,high) in bounds.items():
        if type(result[key]) is not int or not low<=result[key]<=high:
            raise ValueError('invalid elo_matchmaking.'+key)
    if result['maximum_range']<result['initial_range']:
        raise ValueError('elo_matchmaking.maximum_range must cover initial_range')
    if result['queue_ttl_seconds']<result['any_rating_after_seconds']:
        raise ValueError('elo_matchmaking queue TTL must cover unrestricted wait')
    return result


@dataclass
class _Queued:
    mode:str
    rating:int
    started:float
    touched:float


class EloMatchmaking:
    """Expanding windows with immutable wait origin for repeated advertisements.

    For each search's already-native-eligible candidates, prioritize the pair
    containing the longest-waiting participant, then smaller Elo difference.
    Deterministic owner ID breaks exact ties. The longer participant's window
    controls admission, so a newly-arriving player does not reset an older wait.
    """
    def __init__(self, settings=None, clock=time.monotonic):
        self.settings=validate_config(settings)
        self.clock=clock
        self.queue={}

    @staticmethod
    def _profile(owner,mode,rating):
        if type(owner) is not str or not owner or len(owner)>64:
            raise ValueError('invalid Ranked queue owner')
        if type(mode) is not str or mode not in MODES:
            raise ValueError('invalid Ranked queue mode')
        if type(rating) is not int or not -1000000<=rating<=1000000:
            raise ValueError('invalid Ranked queue rating')

    def _now(self):
        value=self.clock()
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('invalid Ranked queue clock')
        return float(value)

    def prune(self):
        now=self._now()
        ttl=self.settings['queue_ttl_seconds']
        for owner,entry in list(self.queue.items()):
            if now<entry.started or now-entry.touched>=ttl:
                self.queue.pop(owner,None)

    def observe(self,owner,mode,rating):
        self._profile(owner,mode,rating)
        self.prune();now=self._now()
        entry=self.queue.get(owner)
        if entry is None or entry.mode!=mode:
            self.queue[owner]=_Queued(mode,rating,now,now)
        else:
            # Fresh database Elo may change, but a retry/host advertisement
            # never grants a newer entrant priority over the original wait.
            entry.rating=rating;entry.touched=now

    def cancel(self,owner):
        self.queue.pop(owner,None)

    def clear(self,owners):
        for owner in owners:self.cancel(owner)

    def window(self,wait_seconds):
        if type(wait_seconds) not in (int,float) or not math.isfinite(wait_seconds):
            raise ValueError('invalid Ranked queue wait')
        wait=max(0,float(wait_seconds));cfg=self.settings
        if wait>=cfg['any_rating_after_seconds']:
            return None
        steps=int(wait//cfg['expand_interval_seconds'])
        return min(cfg['maximum_range'],cfg['initial_range']+steps*cfg['range_step'])

    def rank_candidates(self,owner,candidates):
        """Return admitted owner IDs. Input is native/settings-eligible ONLY.

        Candidate tuples are (owner_id, verified_mode, freshly_loaded_rating).
        All entries must already have a real enqueue/advertisement timestamp;
        merely considering a stale host must not renew or recreate its wait.
        """
        self.prune();now=self._now();own=self.queue.get(owner)
        if own is None:return []
        own_wait=max(0,now-own.started);ranked=[];seen=set()
        for other,mode,rating in candidates:
            self._profile(other,mode,rating)
            if other==owner or other in seen:continue
            seen.add(other);candidate=self.queue.get(other)
            if candidate is None or candidate.mode!=mode or own.mode!=mode:continue
            age=max(0,now-candidate.started);longest=max(own_wait,age)
            difference=abs(own.rating-rating)
            allowed=self.window(longest)
            if self.settings['enabled'] and allowed is not None and difference>allowed:continue
            ranked.append((-longest,difference,other))
        return [other for _,_,other in sorted(ranked)]


def ranked_session_mode(compatibility):
    """Original mode writer adds namespace*1000 to positive session kind.

    Original1459eac70 maps kinds2/3 to RankMatch;1459ea4a0 maps Single/DP
    to those exact kinds. Zero is a wildcard, never a Ranked declaration.
    """
    if type(compatibility) is not int or not 1<=compatibility<=2**32-1:
        return None
    return {2:'single',3:'dp'}.get((compatibility-1)%1000+1)


class RankedSessionPolicy:
    """Shared across transaction previews; never deep-copy the server callback."""
    def __init__(self, profile, available, settings=None, clock=time.monotonic):
        self.match=EloMatchmaking(settings,clock)
        self.profile=profile;self.available=available;self.cache={};self.cancelled=set()

    def __deepcopy__(self,memo):return self

    def cancel(self,owner):
        self.match.cancel(owner);self.cache.pop(owner,None);self.cancelled.add(owner)

    def forget(self,owner):
        self.match.cancel(owner);self.cache.pop(owner,None);self.cancelled.discard(owner)

    def invalidate_ratings(self):self.cache.clear()

    def _rating(self,owner,mode):
        now=self.match._now();cached=self.cache.get(owner)
        if cached is None or now-cached[0]>=5:
            try:profile=self.profile(owner)
            except Exception as exc:
                logging.getLogger('szero_lan').warning('Ranked rating lookup failed error_type=%s',type(exc).__name__)
                profile=None
            cached=(now,profile);self.cache[owner]=cached
        profile=cached[1]
        if type(profile) is not dict:return None
        for row in profile.get('ranks',[]):
            if type(row) is dict and row.get('mode')==mode and type(row.get('rating')) is int:
                return row['rating']
        return None

    def created(self,owner,native):
        mode=ranked_session_mode(native.get('compatibility')) if type(native) is dict and native.get('profile')==2 and native.get('capacity')==2 else None
        if mode is None:self.cancel(owner);return
        if not self.available():return
        rating=self._rating(owner,mode)
        if rating is not None:
            self.cancelled.discard(owner);self.match.observe(owner,mode,rating)

    def candidates(self,owner,request,sessions):
        native=request.get('native_data') or request.get('query') or {}
        mode=ranked_session_mode(native.get('compatibility')) if request.get('version')==2 else None
        if mode is None:
            self.cancel(owner);return sessions
        if not self.available():return sessions
        rating=self._rating(owner,mode)
        if rating is None:self.cancel(owner);return []
        # Active advertisements retain their original enqueue time. Considering
        # a disconnected/deleted room cannot recreate an eligible candidate.
        now=self.match._now()
        for session in sessions:
            entry=self.match.queue.get(session.creator)
            if entry is not None:entry.touched=now
        self.cancelled.discard(owner);self.match.observe(owner,mode,rating)
        candidates=[];by_owner={}
        for session in sessions:
            data=session.native_data or {}
            other=session.creator
            if other in self.cancelled:continue
            candidate_mode=ranked_session_mode(data.get('compatibility'))
            if data.get('profile')!=2 or session.capacity!=2 or candidate_mode!=mode:continue
            candidate_rating=self._rating(other,mode)
            if candidate_rating is None:continue
            self.match.observe(other,mode,candidate_rating)
            candidates.append((other,mode,candidate_rating));by_owner[other]=session
        admitted=self.match.rank_candidates(owner,candidates)
        return [by_owner[other] for other in admitted]
