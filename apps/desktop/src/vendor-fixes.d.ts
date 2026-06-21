declare module '@xterm/xterm' {
  export interface IDisposable {
    dispose(): void
  }

  export interface ITheme {
    background?: string
    foreground?: string
    cursor?: string
    cursorAccent?: string
    selectionBackground?: string
    black?: string
    red?: string
    green?: string
    yellow?: string
    blue?: string
    magenta?: string
    cyan?: string
    white?: string
    brightBlack?: string
    brightRed?: string
    brightGreen?: string
    brightYellow?: string
    brightBlue?: string
    brightMagenta?: string
    brightCyan?: string
    brightWhite?: string
    [key: string]: string | undefined
  }

  export interface ITerminalAddon {
    activate(terminal: Terminal): void
    dispose(): void
  }

  interface IBufferLine {
    translateToString(trimRight?: boolean, startColumn?: number, endColumn?: number): string
  }

  interface IBuffer {
    baseY: number
    cursorY: number
    length: number
    getLine(index: number): IBufferLine | undefined
  }

  interface IBufferNamespace {
    active: IBuffer
  }

  interface ISelectionPositionPoint {
    x: number
    y: number
  }

  export interface ISelectionPosition {
    end: ISelectionPositionPoint
    start: ISelectionPositionPoint
  }

  export interface ITerminalOptions {
    [key: string]: unknown
    cols?: number
    rows?: number
    theme?: ITheme
  }

  export class Terminal {
    constructor(options?: ITerminalOptions)

    buffer: IBufferNamespace
    cols: number
    options: ITerminalOptions
    rows: number
    unicode: { activeVersion: string }

    attachCustomKeyEventHandler?(handler: (event: KeyboardEvent) => boolean): void
    clear(): void
    clearSelection(): void
    dispose(): void
    focus(): void
    getSelection(): string
    getSelectionPosition(): ISelectionPosition | undefined
    hasSelection(): boolean
    loadAddon(addon: ITerminalAddon): void
    onData(listener: (data: string) => void): IDisposable
    onSelectionChange(listener: () => void): IDisposable
    open(parent: HTMLElement): void
    write(data: string, callback?: () => void): void
  }
}

declare module '@tabler/icons-react' {
  import type * as React from 'react'

  export type IconProps = React.ComponentProps<'svg'> & {
    size?: number | string
    stroke?: number | string
  }

  export type Icon = React.ForwardRefExoticComponent<IconProps & React.RefAttributes<SVGSVGElement>>

  export const IconActivity: Icon
  export const IconAdjustmentsHorizontal: Icon
  export const IconAlertCircle: Icon
  export const IconAlertTriangle: Icon
  export const IconArchive: Icon
  export const IconArchiveOff: Icon
  export const IconArrowUp: Icon
  export const IconArrowUpRight: Icon
  export const IconAt: Icon
  export const IconBell: Icon
  export const IconBolt: Icon
  export const IconBoltFilled: Icon
  export const IconBookmark: Icon
  export const IconBookmarkFilled: Icon
  export const IconBrain: Icon
  export const IconBug: Icon
  export const IconChartBar: Icon
  export const IconCheck: Icon
  export const IconChevronDown: Icon
  export const IconChevronLeft: Icon
  export const IconChevronRight: Icon
  export const IconCircle: Icon
  export const IconCircleCheck: Icon
  export const IconClipboard: Icon
  export const IconClock: Icon
  export const IconCommand: Icon
  export const IconCopy: Icon
  export const IconCpu: Icon
  export const IconDeviceDesktop: Icon
  export const IconDeviceDesktopAnalytics: Icon
  export const IconDeviceFloppy: Icon
  export const IconDots: Icon
  export const IconDotsVertical: Icon
  export const IconDownload: Icon
  export const IconExternalLink: Icon
  export const IconEye: Icon
  export const IconEyeOff: Icon
  export const IconFileText: Icon
  export const IconFolderOpen: Icon
  export const IconGitBranch: Icon
  export const IconGlobe: Icon
  export const IconHash: Icon
  export const IconHelpCircle: Icon
  export const IconInfoCircle: Icon
  export const IconKey: Icon
  export const IconLayersIntersect2: Icon
  export const IconLayoutBottombar: Icon
  export const IconLayoutDashboard: Icon
  export const IconLayoutSidebar: Icon
  export const IconLink: Icon
  export const IconLoader2: Icon
  export const IconLock: Icon
  export const IconLogin: Icon
  export const IconMessage2: Icon
  export const IconMessageCircle: Icon
  export const IconMicrophone: Icon
  export const IconMicrophoneOff: Icon
  export const IconMoon: Icon
  export const IconNotebook: Icon
  export const IconPackage: Icon
  export const IconPalette: Icon
  export const IconPencil: Icon
  export const IconPhoto: Icon
  export const IconPin: Icon
  export const IconPlayerPause: Icon
  export const IconPlayerPlay: Icon
  export const IconPlayerStopFilled: Icon
  export const IconPlus: Icon
  export const IconRefresh: Icon
  export const IconSearch: Icon
  export const IconSend: Icon
  export const IconSettings: Icon
  export const IconSettings2: Icon
  export const IconSparkles: Icon
  export const IconSquare: Icon
  export const IconSteeringWheel: Icon
  export const IconSun: Icon
  export const IconTerminal2: Icon
  export const IconTool: Icon
  export const IconTrash: Icon
  export const IconUpload: Icon
  export const IconUsers: Icon
  export const IconVolume2: Icon
  export const IconVolumeOff: Icon
  export const IconWaveSine: Icon
  export const IconX: Icon
}
