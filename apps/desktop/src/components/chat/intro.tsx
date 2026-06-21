import { useStore } from '@nanostores/react'
import { type CSSProperties, useState } from 'react'

import { $desktopBranding } from '@/store/desktop-branding'

import introCopyJsonl from './intro-copy.jsonl?raw'

type IntroCopy = {
  headline: string
  body: string
}

type IntroCopyRecord = IntroCopy & {
  personality: string
}

export type IntroProps = {
  personality?: string
  seed?: number
}

const NEUTRAL_PERSONALITIES = new Set(['', 'default', 'none', 'neutral'])

const FALLBACK_COPY: IntroCopy[] = [
  {
    headline: 'What are we moving today?',
    body: "Send a bug, branch, plan, or rough idea. I'll inspect the repo and turn it into the next concrete step."
  },
  {
    headline: "What's on your mind?",
    body: "Bring the code, question, or stuck part. I'll read the room before making changes."
  },
  {
    headline: 'What should J.A.R.V.I.S. look at?',
    body: "Send the task, failing path, or half-formed plan. I'll help turn it into action."
  },
  {
    headline: 'Where should we start?',
    body: "Bring the problem, goal, or file. I'll inspect first and keep the next step concrete."
  },
  {
    headline: 'What needs attention?',
    body: "Send the context you have. I'll help sort it into a plan or a fix."
  }
]

function normalizeKey(value?: string): string {
  return (value || '').trim().toLowerCase()
}

function titleize(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function isIntroCopyRecord(value: unknown): value is IntroCopyRecord {
  if (!value || typeof value !== 'object') {
    return false
  }

  const record = value as Record<string, unknown>

  return (
    typeof record.personality === 'string' &&
    typeof record.headline === 'string' &&
    typeof record.body === 'string' &&
    Boolean(record.personality.trim()) &&
    Boolean(record.headline.trim()) &&
    Boolean(record.body.trim())
  )
}

function parseIntroCopy(raw: string): Record<string, IntroCopy[]> {
  const byPersonality: Record<string, IntroCopy[]> = {}

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim()

    if (!trimmed) {
      continue
    }

    try {
      const parsed: unknown = JSON.parse(trimmed)

      if (!isIntroCopyRecord(parsed)) {
        continue
      }

      const key = normalizeKey(parsed.personality)
      byPersonality[key] ??= []
      byPersonality[key].push({
        headline: parsed.headline.trim(),
        body: parsed.body.trim()
      })
    } catch {
      // Bad generated copy should not break the whole desktop app.
    }
  }

  return byPersonality
}

const INTRO_COPY_BY_PERSONALITY = parseIntroCopy(introCopyJsonl)

function neutralCopy(): IntroCopy[] {
  return INTRO_COPY_BY_PERSONALITY.none || INTRO_COPY_BY_PERSONALITY.default || FALLBACK_COPY
}

function fallbackCopyForPersonality(personalityKey: string): IntroCopy[] {
  if (NEUTRAL_PERSONALITIES.has(personalityKey)) {
    return neutralCopy()
  }

  const label = titleize(personalityKey)

  return [
    {
      headline: `${label} mode is on. What should we work on?`,
      body: "Send the task, file, or rough idea. I'll use your configured voice and keep the work grounded in this repo."
    },
    {
      headline: `What does ${label} J.A.R.V.I.S. need to see?`,
      body: "Bring the context or the stuck part. I'll adapt to your configured personality."
    },
    {
      headline: `${label} mode is ready.`,
      body: "Send the problem, file, or idea. I'll follow the personality you've configured."
    },
    {
      headline: `What should ${label} J.A.R.V.I.S. tackle?`,
      body: "Drop the task here. I'll keep the work grounded in the repo."
    },
    {
      headline: 'Where should we begin?',
      body: `Give me the context and I'll answer in ${label} mode.`
    }
  ]
}

function pickCopy(copies: IntroCopy[], seed = 0): IntroCopy {
  return copies[Math.abs(seed) % copies.length] || FALLBACK_COPY[0]
}

function resolveLocalCopy(personality?: string, seed?: number): IntroCopy {
  const personalityKey = normalizeKey(personality)

  const copies = NEUTRAL_PERSONALITIES.has(personalityKey)
    ? INTRO_COPY_BY_PERSONALITY[personalityKey] || neutralCopy()
    : INTRO_COPY_BY_PERSONALITY[personalityKey] || fallbackCopyForPersonality(personalityKey)

  return pickCopy(copies, seed)
}

export function Intro({ personality, seed }: IntroProps) {
  const branding = useStore($desktopBranding)
  const [mountSeed] = useState(() => Math.floor(Math.random() * 100000))
  const effectiveSeed = mountSeed + (seed ?? 0)

  const copy = branding.source === 'fallback'
    ? resolveLocalCopy(personality, effectiveSeed)
    : pickCopy(branding.intro_copy, effectiveSeed)

  const accent = branding.theme.accent
  const accentSoft = branding.theme.accent_soft
  const textColor = branding.theme.text

  const wordmarkStyle = {
    '--fit-min': '2.75rem',
    color: textColor
  } as CSSProperties

  return (
    <div
      className="pointer-events-none flex w-full min-w-0 flex-col items-center justify-center px-0.5 py-6 text-center text-muted-foreground sm:px-6 lg:px-8"
      data-slot="aui_intro"
    >
      <div className="w-full min-w-0">
        <div className="mx-auto max-w-3xl rounded-[1.6rem] border border-border/50 bg-background/20 px-6 py-8 shadow-[0_24px_60px_rgba(0,0,0,0.22)] backdrop-blur-sm sm:px-8">
          <div
            className="mx-auto mb-5 grid h-24 w-24 place-items-center rounded-full border bg-gradient-to-b from-white/5 to-transparent"
            style={{ borderColor: accentSoft, boxShadow: `inset 0 0 28px ${accentSoft}` }}
          >
            <div
              className="grid h-14 w-14 place-items-center rounded-full text-lg font-extrabold tracking-[0.12em] shadow-[0_0_32px_rgba(34,211,238,0.25)]"
              style={{
                backgroundImage: `radial-gradient(circle, ${textColor} 0%, ${accentSoft} 38%, rgba(0,0,0,0) 72%)`,
                boxShadow: `0 0 32px ${accentSoft}`,
                color: textColor
              }}
            >
              {branding.avatar_letter}
            </div>
          </div>

          <div
            className="mb-4 inline-flex items-center gap-2 rounded-full border bg-background/45 px-4 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.24em]"
            style={{ borderColor: accentSoft, color: textColor }}
          >
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: accent, boxShadow: `0 0 14px ${accent}` }} />
            <span>{branding.status_label}</span>
          </div>

          <p
            aria-label={branding.wordmark}
            className="fit-text mx-auto mb-2 w-[calc(100%-1rem)] font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] mix-blend-plus-lighter"
            style={wordmarkStyle}
          >
            <span>
              <span>{branding.wordmark}</span>
            </span>
            <span aria-hidden="true">{branding.wordmark}</span>
          </p>

          <p className="mb-4 text-center text-[0.72rem] uppercase tracking-[0.28em] text-muted-foreground/80">
            {branding.tagline}
          </p>

          <div
            className="mx-auto mb-5 h-px w-28"
            style={{ backgroundImage: `linear-gradient(to right, transparent, ${accent}, transparent)` }}
          />

          <p className="mb-2 text-center text-base font-medium tracking-tight text-foreground/90">{copy.headline}</p>
          <p className="m-0 mx-auto max-w-[32rem] text-center leading-relaxed tracking-tight text-muted-foreground">
            {copy.body}
          </p>
        </div>
      </div>
    </div>
  )
}
