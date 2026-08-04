/**
 * A lesson's video link, turned into something safe to embed.
 *
 * The id is pulled out of the URL and a fresh embed URL is built from it. The
 * author's string is never put into an iframe `src` directly: a lesson body is
 * content, content gets edited, and "it came from our own database" is not the
 * same as "it is a YouTube URL". Anything not on the list below is not
 * embedded at all -- it is offered as a plain link instead, which is the
 * honest failure and costs the reader one click.
 */

export type Embed =
  | { kind: 'iframe'; src: string; provider: 'YouTube' | 'Vimeo' }
  | { kind: 'file'; src: string }
  | { kind: 'link'; src: string }

const YOUTUBE_ID = /^[\w-]{11}$/
const VIMEO_ID = /^\d+$/

export function toEmbed(raw: string): Embed {
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return { kind: 'link', src: raw }
  }

  // Nothing is embedded over plain http -- the page is served over https and
  // the frame would be blocked as mixed content anyway.
  if (url.protocol !== 'https:') return { kind: 'link', src: raw }

  const host = url.hostname.replace(/^www\./, '')

  if (host === 'youtube.com' || host === 'm.youtube.com') {
    const id = url.searchParams.get('v') ?? ''
    if (YOUTUBE_ID.test(id)) {
      return {
        kind: 'iframe',
        // nocookie: a lesson page should not set advertising cookies on a
        // student before they have decided to watch anything.
        src: `https://www.youtube-nocookie.com/embed/${id}`,
        provider: 'YouTube',
      }
    }
  }

  if (host === 'youtu.be') {
    const id = url.pathname.slice(1)
    if (YOUTUBE_ID.test(id)) {
      return {
        kind: 'iframe',
        src: `https://www.youtube-nocookie.com/embed/${id}`,
        provider: 'YouTube',
      }
    }
  }

  if (host === 'vimeo.com') {
    const id = url.pathname.split('/').filter(Boolean)[0] ?? ''
    if (VIMEO_ID.test(id)) {
      return {
        kind: 'iframe',
        src: `https://player.vimeo.com/video/${id}`,
        provider: 'Vimeo',
      }
    }
  }

  if (/\.(mp4|webm|ogg)$/i.test(url.pathname)) {
    return { kind: 'file', src: url.href }
  }

  return { kind: 'link', src: raw }
}
