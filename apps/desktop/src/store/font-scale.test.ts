import { beforeEach, describe, expect, it } from 'vitest'

const KEY = 'hermes.desktop.font-scale.v1'

async function loadStore() {
  return import(`./font-scale?case=${Math.random()}`)
}

describe('font scale store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.style.removeProperty('--dt-base-size')
  })

  it('defaults to 100 and applies 1rem to the root token', async () => {
    const mod = await loadStore()

    expect(mod.$fontScale.get()).toBe(100)
    expect(document.documentElement.style.getPropertyValue('--dt-base-size')).toBe('1rem')
  })

  it('clamps and persists updates in 5-point steps', async () => {
    const mod = await loadStore()

    mod.setFontScale(117)
    expect(mod.$fontScale.get()).toBe(115)
    expect(window.localStorage.getItem(KEY)).toBe('115')
    expect(document.documentElement.style.getPropertyValue('--dt-base-size')).toBe('1.15rem')

    mod.setFontScale(999)
    expect(mod.$fontScale.get()).toBe(130)
    expect(window.localStorage.getItem(KEY)).toBe('130')
    expect(document.documentElement.style.getPropertyValue('--dt-base-size')).toBe('1.3rem')
  })
})
