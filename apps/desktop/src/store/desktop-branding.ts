import { atom } from 'nanostores'

import { type DesktopBrandingResponse, getDesktopBranding } from '@/hermes'
import { normalizeProfileKey } from '@/store/profile'

export const DEFAULT_DESKTOP_BRANDING: DesktopBrandingResponse = {
  avatar_letter: 'J',
  intro_copy: [
    {
      headline: 'What should J.A.R.V.I.S. look at?',
      body: "Send the task, failing path, or half-formed plan. I'll help turn it into action."
    },
    {
      headline: 'Where should we start?',
      body: "Bring the problem, goal, or file. I'll inspect first and keep the next step concrete."
    }
  ],
  profile: 'default',
  source: 'fallback',
  status_label: 'Autonomous operator',
  tagline: 'Just A Rather Very Intelligent System',
  theme: {
    accent: '#22d3ee',
    accent_soft: 'rgba(34,211,238,0.18)',
    text: '#e6f7ff'
  },
  version: 1,
  wordmark: 'J.A.R.V.I.S.'
}

export const $desktopBranding = atom<DesktopBrandingResponse>(DEFAULT_DESKTOP_BRANDING)

let requestVersion = 0

export async function refreshDesktopBranding(profile?: null | string): Promise<void> {
  const targetProfile = normalizeProfileKey(profile)
  const version = ++requestVersion

  try {
    const next = await getDesktopBranding()

    if (version !== requestVersion) {
      return
    }

    $desktopBranding.set({ ...next, profile: normalizeProfileKey(next.profile || targetProfile) })
  } catch {
    if (version !== requestVersion) {
      return
    }

    $desktopBranding.set({ ...DEFAULT_DESKTOP_BRANDING, profile: targetProfile })
  }
}
