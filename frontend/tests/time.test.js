import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import { formatDateTime, formatTimeRange } from '../src/stores/dict.js'

const moduleUrl = new URL('../src/stores/dict.js', import.meta.url).href

for (const timezone of ['UTC', 'Asia/Shanghai', 'America/New_York']) {
  test(`课堂显示和编辑在 ${timezone} 环境下都使用北京时间`, () => {
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', `
      import { formatDateTime, formatTimeRange, formatDateTimeInput, toApiDateTime } from ${JSON.stringify(moduleUrl)}
      const start = '2026-10-31T10:23:26Z'
      console.log(JSON.stringify({
        display: formatDateTime(start),
        offsetDisplay: formatDateTime('2026-10-31T18:23:26+08:00'),
        range: formatTimeRange(start, '2026-10-31T11:23:26Z'),
        midnightRange: formatTimeRange('2026-10-31T15:30:00Z', '2026-10-31T16:30:00Z'),
        edit: formatDateTimeInput(start),
        unchanged: toApiDateTime(formatDateTimeInput(start)),
        midnight: toApiDateTime('2026-11-01 00:05:00')
      }))
    `], { encoding: 'utf8', env: { ...process.env, TZ: timezone } })
    assert.equal(result.status, 0, result.stderr)
    assert.deepEqual(JSON.parse(result.stdout), {
      display: '2026-10-31 18:23',
      offsetDisplay: '2026-10-31 18:23',
      range: '10月31日 18:23 至 19:23',
      midnightRange: '10月31日 23:30 至 11月1日 00:30',
      edit: '2026-10-31 18:23:26',
      unchanged: '2026-10-31T10:23:26.000Z',
      midnight: '2026-10-31T16:05:00.000Z'
    })
  })
}

test('空值和非法时间不显示成有效课堂时间', () => {
  assert.equal(formatDateTime(null), '—')
  assert.equal(formatDateTime('invalid'), '—')
  assert.equal(formatTimeRange(null, '2026-10-31T10:23:26Z'), '—')
})
