#!/usr/bin/env python3
"""Generate reviewed native relocation recipes from two read-only PE references.

Development tool only: requires pefile and GNU objdump. It never runs a game or
writes either reference. The shipped C catalog contains small instruction
patterns, not either executable, credentials, or an executable digest gate.
Every pattern must be unique in BOTH inputs and retain instruction/field bytes;
only decoded relative displacements are wildcarded. Data addresses are obtained
from decoded instructions, never a guessed section-wide displacement.
"""
from __future__ import annotations
import argparse
import bisect
import json
import re
import struct
import subprocess
from pathlib import Path
import pefile


class Image:
    def __init__(self, path):
        self.path = Path(path)
        self.pe = pefile.PE(str(path), fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.text = next(s for s in self.pe.sections if s.Name.rstrip(b'\0') == b'.text')
        self.code = self.text.get_data()[:self.text.Misc_VirtualSize]
        self.rva = self.text.VirtualAddress
        pdata = next(s for s in self.pe.sections if s.Name.rstrip(b'\0') == b'.pdata').get_data()
        self.ranges = {a: b for a, b, _ in struct.iter_unpack('<III', pdata[:len(pdata)//12*12]) if a and b > a}
        self.starts = sorted(self.ranges)
        self._dis = {}

    def data(self, rva, length):
        return self.pe.get_data(rva, length)

    def function(self, rva):
        at = bisect.bisect_right(self.starts, rva) - 1
        if at >= 0:
            start = self.starts[at]
            if start <= rva < self.ranges[start]:
                return start, self.ranges[start] - start
        return rva, 32

    def dis(self, rva, length):
        key = rva, length
        if key in self._dis:
            return self._dis[key]
        out = subprocess.check_output(['objdump', '-d', '--insn-width=16', '--start-address='+hex(self.base+rva),
                                       '--stop-address='+hex(self.base+rva+length), str(self.path)], text=True)
        result = []
        for line in out.splitlines():
            match = re.match(r'\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*(.*)', line)
            if match:
                result.append((int(match[1], 16)-self.base, bytes.fromhex(match[2]), match[3]))
        self._dis[key] = result
        return result

    def signature(self, rva, length):
        data = self.data(rva, length)
        mask = bytearray(b'\xff'*len(data))
        refs = []
        for at, bs, op in self.dis(rva, length+16):
            if at-rva>=len(data):break
            offset = at-rva
            if offset+len(bs) > len(data):
                # Never leave a partly decoded displacement in a pattern.
                data = data[:offset]
                mask = mask[:offset]
                break
            if '(%rip)' in op:
                match = re.search(r'#\s*(?:0x)?([0-9a-f]+)', op)
                if match:
                    target = int(match[1], 16)-self.base
                    packed = struct.pack('<i', target-(at+len(bs)))
                    where = bs.find(packed)
                    if where >= 0:
                        mask[offset+where:offset+where+4] = b'\0'*4
                        refs.append((offset, where, len(bs), target))
            if bs[0] in (0xe8, 0xe9) and len(bs) == 5:
                mask[offset+1:offset+5] = b'\0'*4
                refs.append((offset, 1, 5, at+5+struct.unpack('<i', bs[1:])[0]))
        return data, bytes(mask), refs

    def find(self, data, mask):
        best = (0, 0)
        start = 0
        for i, bit in enumerate(mask+b'\0'):
            if not bit:
                if i-start > best[1]-best[0]:
                    best = start, i
                start = i+1
        a, b = best
        if b-a < 4:
            return []
        result = []
        at = 0
        while (at := self.code.find(data[a:b], at)) >= 0:
            pos = at-a
            at += 1
            if pos >= 0 and pos+len(data) <= len(self.code) and all(not m or self.code[pos+i] == data[i] for i, m in enumerate(mask)):
                result.append(self.rva+pos)
                if len(result) > 32:
                    break
        return result


def literal(data):
    return '{'+','.join('0x%02x'%b for b in data)+'}'


def constrained_matches(image,data,mask,constraint):
    found=image.find(data,mask)
    if not constraint:return found
    offset=constraint['instruction_offset'];disp=constraint['displacement_offset'];size=constraint['instruction_size']
    literal=bytes.fromhex(constraint['bytes'])
    result=[]
    for start in found:
        target=start+offset+size+struct.unpack('<i',image.data(start+offset+disp,4))[0]
        if image.data(target,len(literal))==literal:result.append(start)
    return result


def generate(old, new, inventory, mapping, data_recipes, output):
    old = Image(old)
    new = Image(new)
    binding_map = mapping.get('bindings', mapping)
    recipes = []
    entries = []
    references = []
    prefix_references = []
    normalized = []
    required = [int(b['rva'], 16) for b in inventory['bindings'] if int(b['rva'], 16) != 0x8cf8500]
    available = set(required)
    derived = {0x6d36f88: (0x6d36f80, 8), 0x6d36f98: (0x6d36f80, 24)}
    for canonical in required:
        info = binding_map.get(hex(canonical))
        if not info:
            raise ValueError('Unmapped binding '+hex(canonical))
        actual = int(info['new_rva'], 16) if isinstance(info['new_rva'], str) else info['new_rva']
        section = next(s for s in old.pe.sections if s.VirtualAddress <= canonical < s.VirtualAddress+s.Misc_VirtualSize)
        executable = bool(section.Characteristics & 0x20000000)
        first = len(recipes)
        prefix, pmask, prefs = old.signature(canonical, 32) if executable else (b'', b'', [])
        for offset,disp,insn,target in prefs:
            target_section=next((section for section in old.pe.sections if section.VirtualAddress<=target<section.VirtualAddress+section.Misc_VirtualSize),None)
            if target_section is not None:
                prefix_references.append((canonical,offset,disp,insn,target if target in available else 0,target_section.Characteristics&(0x20000000|0x80000000)))
        if executable:
            start, size = old.function(canonical)
            if canonical!=start:
                # A callsite is its own instruction anchor; embedded RVA jump
                # tables elsewhere in the containing body are not instructions.
                start,size=canonical,64
            delta = canonical-start
            # Hooks own the first 14-16 bytes. Anchor beyond that region so
            # independently loaded helpers can resolve after another helper
            # installed its owned MinHook trampoline.
            if size >= 48:
                adjusted=next(at for at,_,_ in old.dis(start,min(size,128)) if at>=start+32)
                size-=adjusted-start
                delta-=adjusted-start
                start=adjusted
            recipe = None
            # Small/common leaves include neighbouring instructions to anchor
            # their position without guessing which identical stub is intended.
            for length in sorted(set([max(size, 32), 64, 128, 256, 512, 1024, 2048, max(size, delta+32)])):
                if length > 32768:
                    continue
                data, mask, refs = old.signature(start, length)
                if delta >= 0 and len(data) <= delta:
                    continue
                if old.find(data, mask) != [start]:
                    continue
                matches = new.find(data, mask)
                if matches != [actual-delta]:
                    continue
                recipe = {'canonical':canonical,'old_anchor':start,'new_anchor':actual-delta,'data':data,'mask':mask,
                          'kind':0,'result_offset':delta,'disp':0,'insn':0,'constraint':None}
                for offset, disp, insn, target in refs:
                    if target in available:
                        references.append((canonical, offset-delta, disp, insn, target))
                break
            if recipe is None:
                raise ValueError('No unique normalized instruction pattern for '+hex(canonical))
            recipes.append(recipe)
            normalized.append({'canonical':hex(canonical),'new_rva':hex(actual),'anchor':hex(start),'length':len(recipe['data'])})
        else:
            parent, add = derived.get(canonical, (canonical, 0))
            candidates = data_recipes.get(hex(parent), {}).get('recipes', [])
            if not candidates:
                raise ValueError('No data recipe for '+hex(canonical))
            for candidate in candidates[:2]:
                start = int(candidate['anchor_old'], 16)
                newstart = int(candidate['anchor_new'], 16)
                data,mask,_ = old.signature(start,candidate.get('length',len(bytes.fromhex(candidate.get('signature_bytes','')))))
                constraint=candidate.get('literal_constraint')
                if constrained_matches(old,data,mask,constraint) != [start] or constrained_matches(new,data,mask,constraint) != [newstart]:
                    raise ValueError('Ambiguous data anchor '+hex(canonical))
                offset = candidate.get('target_instruction_offset',0)
                disp = offset+candidate['disp_offset']
                insn = offset+candidate['instruction_size']
                decoded = newstart+insn+struct.unpack('<i', new.data(newstart+disp,4))[0]+add
                if decoded != actual:
                    raise ValueError('Incorrect data recipe '+hex(canonical))
                recipes.append({'canonical':canonical,'old_anchor':start,'new_anchor':newstart,'data':data,'mask':mask,
                                'kind':1,'result_offset':add,'disp':disp,'insn':insn,'constraint':constraint})
        entries.append({'canonical':canonical,'actual':actual,'first':first,'count':len(recipes)-first,
                        'flags':section.Characteristics & (0x20000000|0x80000000),'prefix':prefix,'pmask':pmask})
    blob = bytearray()
    for r in recipes:
        r['blob'] = len(blob)
        blob.extend(r['data'])
        r['mask_blob'] = len(blob)
        blob.extend(r['mask'])
        best=(0,0)
        at=0
        for i,b in enumerate(r['mask']+b'\0'):
            if not b:
                if i-at>best[1]-best[0]: best=at,i
                at=i+1
        r['anchor_offset'],r['anchor_length']=best[0],best[1]-best[0]
        c=r['constraint']
        r['constraint_blob']=len(blob)
        if c:blob.extend(bytes.fromhex(c['bytes']))
    lines=['/* Generated by generate_native_bindings.py; no executable digest gate. */',
           'static const unsigned char binding_bytes[] = '+literal(blob)+';',
           'static const BindingRecipe binding_recipes[] = {']
    for r in recipes:
        c=r['constraint']
        lines.append(' {%du,%du,%du,%du,%du,%du,%d,%du,%du,%du,%du,%du,%du,%du},' %
                     (r['blob'],r['mask_blob'],len(r['data']),r['anchor_offset'],r['anchor_length'],r['kind'],r['result_offset'],r['disp'],r['insn'],r['canonical'],
                      r['constraint_blob'],len(bytes.fromhex(c['bytes'])) if c else 0,c['instruction_offset']+c['displacement_offset'] if c else 0,c['instruction_offset']+c['instruction_size'] if c else 0))
    lines += ['};','static const BindingEntry binding_entries[] = {']
    for e in entries:
        lines.append(' {0x%xu,0x%xu,0x%xu,%du,%du,0x%xu,%du,%s,%s},' %
                     (e['canonical'],e['canonical'],e['actual'],e['first'],e['count'],e['flags'],len(e['prefix']),literal(e['prefix'] or bytes(32)),literal(e['pmask'] or bytes(32))))
    lines += ['};','static const BindingReference binding_references[] = {']
    for canonical,offset,disp,insn,target in sorted(set(references)):
        lines.append(' {0x%xu,%d,%du,%du,0x%xu},'%(canonical,offset,disp,insn,target))
    lines += ['};','static const BindingPrefixReference binding_prefix_references[] = {']
    for canonical,offset,disp,insn,target,flags in sorted(set(prefix_references)):
        lines.append(' {0x%xu,%d,%du,%du,0x%xu,0x%xu},'%(canonical,offset,disp,insn,target,flags))
    lines += ['};','']
    Path(output).write_text('\n'.join(lines))
    return {'binding_count':len(entries),'recipe_count':len(recipes),'reference_count':len(set(references)),'prefix_reference_count':len(set(prefix_references)),
            'pattern_bytes':len(blob),'patterns':normalized,'verified_old_and_updated':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',required=True)
    p.add_argument('--updated',required=True)
    p.add_argument('--recipes',default=str(Path(__file__).with_name('native')/'native_bindings_recipes.json'))
    p.add_argument('--inventory')
    p.add_argument('--mapping')
    p.add_argument('--data-recipes')
    p.add_argument('--special-recipes')
    p.add_argument('--output',default='lan/native/native_bindings_catalog.h')
    p.add_argument('--report')
    a=p.parse_args()
    manifest=json.loads(Path(a.recipes).read_text())
    inventory=json.loads(Path(a.inventory).read_text()) if a.inventory else manifest['inventory']
    mapping=json.loads(Path(a.mapping).read_text()) if a.mapping else manifest['mapping']
    recipes=json.loads(Path(a.data_recipes).read_text()) if a.data_recipes else manifest['data_recipes']
    if a.special_recipes:
        for key,values in json.loads(Path(a.special_recipes).read_text()).items():recipes[key]={'recipes':values}
    result=generate(a.old,a.updated,inventory,mapping,recipes,a.output)
    if a.report: Path(a.report).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='patterns'}))

if __name__=='__main__':main()
