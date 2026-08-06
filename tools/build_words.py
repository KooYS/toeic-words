"""학습가이드.pdf 색인 순서대로 word.xls를 정렬해 words.json 생성."""
import json, re, collections, fitz, xlrd

BASE = '/Users/koo/Downloads/words'
LESSON = re.compile(r'^(\d{1,2}강|보충어휘)(.*)$')   # 드물게 '보충어휘convert' 처럼 붙어 나옴

def norm(s):
    return re.sub(r'\s+', '', s).lower()

def pdf_index():
    """3단 조판. 순번 토큰을 앵커로 두고 본문 토큰을 y가 가장 가까운 앵커에 붙인다.
    긴 숙어는 두 줄로 접히는데 순번이 아랫줄에 찍히므로, 등거리면 아래쪽 앵커를 택한다."""
    doc = fitz.open(f'{BASE}/학습가이드.pdf')
    out = []
    for page in doc[1:]:                        # 1p는 학습플랜, 2p부터 색인
        cols = collections.defaultdict(list)
        for x0, y0, x1, y1, t, *_ in page.get_text('words'):
            if y1 < 75:                         # 페이지 머리말 "경선식의 토익영단어"
                continue
            cols[0 if x0 < 255 else 1 if x0 < 475 else 2].append(((y0 + y1) / 2, x0, t))

        for c in sorted(cols):
            toks = sorted(cols[c], key=lambda w: (round(w[0] / 4), w[1]))
            anchors, rest = [], []
            for i, (y, x, t) in enumerate(toks):
                m = LESSON.match(t) if i and toks[i - 1][2].isdigit() else None
                if m:
                    anchors.append((y, int(toks[i - 1][2]), m[1], [(y, x, m[2])] if m[2] else []))
                elif not (t.isdigit() and i + 1 < len(toks) and LESSON.match(toks[i + 1][2])):
                    rest.append((y, x, t))
            if not anchors:
                continue
            for y, x, t in rest:
                a = min(anchors, key=lambda a: (round(abs(a[0] - y), 1), -a[0]))
                a[3].append((y, x, t))
            for _, seq, lesson, words in anchors:
                text = ' '.join(t for _, _, t in sorted(words, key=lambda w: (round(w[0] / 4), w[1])))
                out.append((seq, lesson, text))
    return sorted(out)

def xls_rows():
    sh = xlrd.open_workbook(f'{BASE}/word.xls').sheet_by_index(0)
    return [tuple(str(c).strip() for c in sh.row_values(r)[:3]) for r in range(1, sh.nrows)]

idx, rows = pdf_index(), xls_rows()
pool = collections.defaultdict(collections.deque)
for lesson, word, meaning in rows:
    pool[(lesson, norm(word))].append((word, meaning))

out, unmatched = [], []
for seq, lesson, word in idx:
    q = pool.get((lesson, norm(word)))
    if not q:   # PDF와 xls 표기가 다른 경우(부연설명 유무) 같은 강 안에서 접두 매칭
        cand = [k for k, v in pool.items()
                if k[0] == lesson and v and k[1].startswith(norm(word))]
        q = pool[cand[0]] if len(cand) == 1 else None
    if q:
        w, m = q.popleft()
        out.append({'seq': seq, 'lesson': lesson, 'word': w, 'meaning': m})
    else:
        unmatched.append((seq, lesson, word))

leftover = [(k[0], w, m) for k, q in pool.items() for w, m in q]
# PDF 1957번은 조판 누락(빈 칸) — 남은 행이 1개면 그 자리에 채운다
if not unmatched and len(leftover) == 1:
    lesson, word, meaning = leftover.pop()
    out.append({'seq': 1957, 'lesson': lesson, 'word': word, 'meaning': meaning})
    out.sort(key=lambda d: d['seq'])

assert not unmatched, f'PDF에만 있는 항목: {unmatched[:10]}'
assert not leftover, f'xls에만 남은 항목: {leftover[:10]}'
assert [d['seq'] for d in out] == list(range(1, len(out) + 1)), '순번 불연속'

with open(f'{BASE}/words.json', 'w') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'words.json {len(out)}개 — PDF 색인과 1:1 전부 매칭')
for i in (0, 1, 1956, 2189):
    print(' ', out[i])
