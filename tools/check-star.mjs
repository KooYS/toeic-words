// 찜은 seq 하나만 서버에 저장한다 (stars 테이블의 PK가 user_id + seq).
// seq 가 겹치면 별 하나가 단어 여러 개를 가리키게 되므로 기능 전체가 무너진다.
// 같은 강에 같은 철자가 여러 번 나오는 경우가 있어서(raise, charge 등) 철자로는 못 센다.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const load = f => JSON.parse(readFileSync(new URL(f, import.meta.url)))
const segs = load('../segments.json')
const words = load('../words.json')

let bad = 0
const fail = m => { console.log('✕ ' + m); bad++ }

// 1. segments.json 안에서 seq 는 고유해야 한다
const seen = new Map()
for (const s of segs) {
  if (seen.has(s.seq)) fail(`seq ${s.seq} 중복: ${seen.get(s.seq)} / ${s.word}`)
  seen.set(s.seq, s.word)
}

// 2. seq 는 int 여야 한다 (Postgres 컬럼이 int)
for (const s of segs)
  if (!Number.isInteger(s.seq) || s.seq < 1) fail(`seq 가 정수가 아님: ${JSON.stringify(s.seq)}`)

// 3. words.json 의 seq 와 같은 것을 가리켜야 한다.
//    78·79강이 빠져서 개수는 다르지만, 겹치는 seq 는 같은 단어여야 한다.
const byWords = new Map(words.map(w => [w.seq, w]))
for (const s of segs) {
  const w = byWords.get(s.seq)
  if (!w) fail(`seq ${s.seq} (${s.word}) 가 words.json 에 없음`)
  else if (w.word !== s.word) fail(`seq ${s.seq}: segments=${s.word} / words=${w.word}`)
}

console.log(bad ? `\n${bad}건 실패` : `✓ seq 고유 · 정수 · words.json 과 일치 (${segs.length}개)`)
process.exit(bad ? 1 : 0)
