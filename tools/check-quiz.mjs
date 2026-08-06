// 퀴즈 보기 충돌 검사. index.html 안의 퀴즈 로직을 그대로 꺼내 전체 단어로 돌린다.
//   node tools/check-quiz.mjs
import fs from 'fs'

const root = new URL('..', import.meta.url).pathname
const html = fs.readFileSync(root + 'index.html', 'utf8')
const segs = JSON.parse(fs.readFileSync(root + 'segments.json', 'utf8'))

const src = html.split('/* ---------- 퀴즈 ---------- */')[1].split('</script>')[0]

const meaningsOf = new Map(), wordsOf = new Map()
for (const s of segs) {
  if (!meaningsOf.has(s.word)) meaningsOf.set(s.word, new Set())
  if (!wordsOf.has(s.meaning)) wordsOf.set(s.meaning, new Set())
  meaningsOf.get(s.word).add(s.meaning)
  wordsOf.get(s.meaning).add(s.word)
}

const el = () => ({ onclick: null, innerHTML: '', append() {}, querySelector: el, children: [] })
const { makeQ } = new Function(
  'segs', 'meaningsOf', 'wordsOf', '$', 'show', 'picked',
  src + '; return { makeQ }'
)(segs, meaningsOf, wordsOf, el, () => {}, () => segs)

let meaningQ = 0, wordQ = 0
for (const e of segs) {
  for (let n = 0; n < 3; n++) {                 // 무작위라 항목마다 여러 번
    const q = makeQ(e, segs)
    console.assert(q.opts.length === 4, `보기 4개 아님: ${e.word}`)
    console.assert(new Set(q.opts).size === 4, `보기 중복: ${e.word} ${JSON.stringify(q.opts)}`)
    console.assert(q.opts.includes(q.answer), `정답 누락: ${e.word}`)

    const others = q.opts.filter(o => o !== q.answer)
    if (q.type === '뜻 고르기') {
      meaningQ++
      // raise 처럼 같은 철자가 갖는 다른 뜻이 보기에 섞이면 정답이 둘 이상이 된다
      const bad = others.filter(o => meaningsOf.get(e.word).has(o))
      console.assert(!bad.length, `[뜻 고르기] ${e.word} 보기에 같은 철자의 다른 뜻: ${bad}`)
    } else {
      wordQ++
      const bad = others.filter(o => wordsOf.get(e.meaning).has(o))
      console.assert(!bad.length, `[단어 고르기] "${e.meaning}" 보기에 같은 뜻의 다른 철자: ${bad}`)
    }
  }
}

// 여러 뜻으로 쪼개진 철자가 실제로 검사에 포함됐는지 (검사가 헛돌지 않았는지)
const dup = [...meaningsOf].filter(([, v]) => v.size > 1)
console.log(`문항 ${meaningQ + wordQ}개 검사 — 뜻 고르기 ${meaningQ} / 단어 고르기 ${wordQ}`)
console.log(`뜻이 여러 개인 철자 ${dup.length}개 포함 (예: ${dup.slice(0, 5).map(([k]) => k).join(', ')})`)
console.log('충돌 없음')
