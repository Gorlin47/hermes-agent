/**
 * Desktop text scale.
 *
 * A single desktop-only preference that scales the renderer's root `rem` size.
 * Because the app's typography mostly hangs off rem-based tokens, this enlarges
 * both chat text and the surrounding UI without having to hand-tune every
 * component.
 */

import { atom } from 'nanostores'

import { persistString, storedString } from '@/lib/storage'

const KEY = 'hermes.desktop.font-scale.v1'
const DEFAULT = 100
const MIN = 90
const MAX = 130

const clamp = (value: number): number => Math.min(MAX, Math.max(MIN, Math.round(value / 5) * 5))

const read = (): number => {
  const value = Number(storedString(KEY))

  return Number.isFinite(value) ? clamp(value) : DEFAULT
}

function applyFontScale(scale: number): void {
  if (typeof document === 'undefined') {
    return
  }

  document.documentElement.style.setProperty('--dt-base-size', `${scale / 100}rem`)
}

export const $fontScale = atom<number>(typeof window === 'undefined' ? DEFAULT : read())

export function setFontScale(scale: number): void {
  $fontScale.set(clamp(scale))
}

if (typeof window !== 'undefined') {
  applyFontScale($fontScale.get())

  $fontScale.subscribe(scale => {
    persistString(KEY, String(scale))
    applyFontScale(scale)
  })
}

export const FONT_SCALE_MIN = MIN
export const FONT_SCALE_MAX = MAX
export const FONT_SCALE_DEFAULT = DEFAULT
