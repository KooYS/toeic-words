"""강별 mp3를 단어 단위 [start, end] 오프셋으로 쪼개 segments.json 생성.
단어 클립 사이에는 1.0초 디지털 무음이 삽입돼 있고 단어 내부 최장 쉼은 0.74초라
-70dB 기준 무음 중 긴 것 n-1개를 고르면 경계가 된다. (n = 해당 강 단어 수)"""
import json, re, subprocess, collections, sys

BASE = '/Users/koo/Downloads/words'
LEAD, TAIL = 0.10, 0.25   # 소리 시작 앞 / 끝 뒤로 남길 여유

def probe(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'csv=p=0', f], capture_output=True, text=True).stdout)

def word_end(allsil, s, e):
    """클립은 [영단어][영단어 반복][뜻...] 구조다. 앞 두 덩어리는 영단어 글자수와
    상관 0.6~0.8, 세 번째부터는 뜻 글자수와 상관 0.7~0.9. 두 번째 덩어리 끝까지가 영단어."""
    gaps = [(a, b) for a, b in allsil if s < a and b < e]
    return min(e, gaps[1][0] + TAIL) if len(gaps) >= 2 else e


def silences(f):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', f, '-af',
                          'silencedetect=noise=-70dB:d=0.25', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    e = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    return list(zip(s, e))

words = json.load(open(f'{BASE}/words.json'))
by_lesson = collections.defaultdict(list)
for w in words:
    by_lesson[w['lesson']].append(w)

segs, report = [], []
for lesson, ws in sorted(by_lesson.items(), key=lambda kv: kv[1][0]['seq']):
    num = re.sub(r'\D', '', lesson)
    mp3 = f'{BASE}/mp3/{num.zfill(2)}강.mp3' if num else f'{BASE}/mp3/보충어휘.mp3'
    try:
        total = probe(mp3)
    except ValueError:
        report.append((lesson, len(ws), None, None, 'mp3 없음'))
        continue

    allsil = silences(mp3)
    inner = [(a, b) for a, b in allsil if a > 0.3 and b < total - 0.3]
    need = len(ws) - 1
    ranked = sorted(inner, key=lambda g: g[1] - g[0], reverse=True)
    picked = sorted(ranked[:need])
    # 채택한 것 중 가장 짧은 무음 vs 탈락한 것 중 가장 긴 무음 = 판정 여유
    margin = ((ranked[need - 1][1] - ranked[need - 1][0]) - (ranked[need][1] - ranked[need][0])
              if len(ranked) > need and need > 0 else None)

    # 무음 한가운데가 아니라 소리가 실제로 시작/끝나는 지점을 경계로 삼는다.
    # 파일 맨 앞뒤 무음도 같은 방식으로 걷어낸다.
    head = [b for a, b in allsil if a <= 0.3]
    foot = [a for a, b in allsil if b >= total - 0.3]
    onsets = [head[0] if head else 0.0] + [b for _, b in picked]
    offsets = [a for a, _ in picked] + [foot[-1] if foot else total]
    lens = []
    for w, s, e in zip(ws, onsets, offsets):
        s, e = max(0.0, s - LEAD), min(total, e + TAIL)
        segs.append({**w, 'file': mp3.split('/')[-1], 'start': round(s, 2), 'end': round(e, 2),
                     'wordEnd': round(word_end(allsil, s, e), 2)})
        lens.append(e - s)
    report.append((lesson, len(ws), round(margin, 2) if margin else None,
                   (round(min(lens), 1), round(max(lens), 1)), 'ok'))

json.dump(segs, open(f'{BASE}/segments.json', 'w'), ensure_ascii=False, indent=1)

bad = [r for r in report if r[4] != 'ok' or (r[2] is not None and r[2] < 0.1)]
print(f'segments.json {len(segs)}개 / 전체 단어 {len(words)}개')
print(f'강 {len(report)}개 중 정상 {sum(1 for r in report if r[4] == "ok")}개')
print('\n판정 여유(초) 최소 10개:')
for r in sorted([r for r in report if r[2] is not None], key=lambda r: r[2])[:10]:
    print(f'  {r[0]:>6}  단어{r[1]:3d}  여유 {r[2]:.2f}s  구간 {r[3][0]}~{r[3][1]}s')
print('\n문제:', [(r[0], r[4]) for r in report if r[4] != 'ok'] or '없음')
