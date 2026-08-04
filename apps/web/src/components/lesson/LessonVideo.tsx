import { toEmbed } from '../../lib/video'

/**
 * One video from the lesson.
 *
 * Lazy-loaded, so opening the Watch tab does not fetch a player for a video
 * nobody scrolled to, and titled from the lesson rather than from the provider.
 *
 * A link that cannot be embedded is shown as a link rather than hidden. The
 * reader can still watch it; only the convenience is lost.
 */
export function LessonVideo({ url, title }: { url: string; title: string }) {
  const embed = toEmbed(url)
  const label = title || 'Lesson video'

  return (
    <figure className="vid">
      <figcaption className="vid-cap">
        <span className="vid-title">{label}</span>
        {embed.kind === 'iframe' && (
          <span className="vid-provider muted small">{embed.provider}</span>
        )}
      </figcaption>

      {embed.kind === 'iframe' && (
        <div className="vid-frame">
          <iframe
            src={embed.src}
            title={label}
            loading="lazy"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      )}

      {embed.kind === 'file' && (
        <div className="vid-frame">
          <video src={embed.src} controls preload="metadata" />
        </div>
      )}

      {embed.kind === 'link' && (
        <p className="vid-fallback">
          This one can&rsquo;t be played here.{' '}
          <a href={embed.src} target="_blank" rel="noreferrer noopener">
            Open it in a new tab →
          </a>
        </p>
      )}
    </figure>
  )
}
