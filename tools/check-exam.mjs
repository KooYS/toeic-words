// 주관식 자동 채점 검사. index.html 안의 채점 로직을 그대로 꺼내 돌린다.
//   node tools/check-exam.mjs
import fs from 'fs'

const root = new URL('..', import.meta.url).pathname
const html = fs.readFileSync(root + 'index.html', 'utf8')
const segs = JSON.parse(fs.readFileSync(root + 'segments.json', 'utf8'))

const src = html.split('/* ---------- 시험 ---------- */')[1].split('</script>')[0]
const el = () => ({ onclick: null, append() {}, replaceChildren() {}, classList: { toggle() {} },
                    children: [], className: '', textContent: '' })
const { senses, autoGrade } = new Function(
  '$', 'show', 'picked', 'shuffle', 'makeQ', 'document', 'scrollTo',
  src + '; return { senses, autoGrade }'
)(el, () => {}, () => segs, a => a, () => ({}),
  { createElement: el, createDocumentFragment: el, addEventListener() {} }, () => {})

let fail = 0
const ok = (given, meaning, want, why) => {
  const got = autoGrade(given, meaning)
  if (got !== want) { fail++; console.error(`  ✕ ${why}\n     "${given}" vs "${meaning}" → ${got}, 기대 ${want}`) }
}

// 뜻이 여러 개면 하나만 맞아도 정답
const share = 'n. 1. 몫, 지분, 주식 2. 공유하다, 나누다'
ok('몫', share, true, '첫 번째 뜻')
ok('주식', share, true, '세 번째 뜻')
ok('공유하다', share, true, '2번 항목의 뜻')
ok('나누다', share, true, '마지막 뜻')
ok('몫, 지분', share, true, '여러 개를 한꺼번에 써도')
ok('공유', share, true, '앞부분만 써도')

// 대괄호는 대체 표현
const caution = 'n. 조심, 경고; 주의[경고]를 주다'
ok('조심', caution, true, '대괄호 앞의 단순 뜻')
ok('주의를 주다', caution, true, '대괄호 원본')
ok('경고를 주다', caution, true, '대괄호 대체형')

// 괄호 안 부연설명은 무시
ok('속하다', 'v. (~에) 속하다', true, '괄호 부연설명 제거')
ok('타다', 'n. 1. 판자, 게시판 2. (차․배․비행기 등을) 타다', true, '긴 괄호 뒤의 뜻')
ok('판자', 'n. 1. 판자, 게시판 2. (차․배․비행기 등을) 타다', true, '괄호 앞의 뜻')

// 오답은 오답
ok('걷다', share, false, '전혀 다른 뜻')
ok('', share, false, '빈 답')
ok('먹다', 'v. 협상하다', false, '무관한 답')
// 흔한 어미로 뭉개서 맞히는 것 차단
ok('하다', share, false, '"하다"만 써서 공유하다에 걸리면 안 됨')
ok('되다', 'v. 제공하다, 제안하다', false, '어미만으로는 불가')

// 전체 뜻으로 senses()가 비는 경우가 없어야 한다 (있으면 그 문제는 영영 오답 처리)
const empty = segs.filter(s => senses(s.meaning).length === 0)
if (empty.length) { fail++; console.error(`  ✕ 후보가 안 나오는 뜻 ${empty.length}개:`, empty.slice(0, 3)) }

// 정답을 그대로 쓰면 당연히 맞아야 한다 — 전체 2092개로 확인
const selfFail = segs.filter(s => !autoGrade(s.meaning, s.meaning))
if (selfFail.length) {
  fail++
  console.error(`  ✕ 정답을 그대로 써도 오답인 항목 ${selfFail.length}개:`,
                selfFail.slice(0, 3).map(s => `${s.word} / ${s.meaning}`))
}

// 첫 번째 뜻만 써도 맞아야 한다
const firstFail = segs.filter(s => { const a = senses(s.meaning)[0]; return a && !autoGrade(a, s.meaning) })
if (firstFail.length) {
  fail++
  console.error(`  ✕ 첫 번째 뜻만 써도 오답인 항목 ${firstFail.length}개:`,
                firstFail.slice(0, 3).map(s => `${s.word} / ${s.meaning}`))
}

console.log(`뜻 ${segs.length}개 + 케이스 18개 검사`)
console.log(`평균 채점 후보 수: ${(segs.reduce((a, s) => a + senses(s.meaning).length, 0) / segs.length).toFixed(1)}개`)
console.log(fail ? `실패 ${fail}건` : '전부 통과')
process.exit(fail ? 1 : 0)
