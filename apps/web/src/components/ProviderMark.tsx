/**
 * Brand marks for the third-party sign-in buttons.
 *
 * Separate from components/Icon.tsx on purpose: those are our own interface
 * icons and inherit `currentColor`, so they restyle with the theme. These are
 * someone else's logo. Both companies' brand terms require the mark to keep its
 * own colours and proportions, so these are drawn at fixed colours and must not
 * be "tidied up" to match the palette.
 */

export function ProviderMark({ name, size = 18 }: { name: string; size?: number }) {
  if (name === 'google') {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden focusable="false">
        <path
          fill="#4285F4"
          d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z"
        />
        <path
          fill="#34A853"
          d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z"
        />
        <path
          fill="#FBBC05"
          d="M11.69 28.18C11.25 26.86 11 25.45 11 24s.25-2.86.69-4.18v-5.7H4.34C2.85 17.09 2 20.45 2 24s.85 6.91 2.34 9.88l7.35-5.7z"
        />
        <path
          fill="#EA4335"
          d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z"
        />
      </svg>
    )
  }

  if (name === 'microsoft') {
    return (
      <svg width={size} height={size} viewBox="0 0 23 23" aria-hidden focusable="false">
        <path fill="#F25022" d="M1 1h10v10H1z" />
        <path fill="#7FBA00" d="M12 1h10v10H12z" />
        <path fill="#00A4EF" d="M1 12h10v10H1z" />
        <path fill="#FFB900" d="M12 12h10v10H12z" />
      </svg>
    )
  }

  if (name === 'apple') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden focusable="false">
        <path
          fill="#000"
          d="M17.05 12.54c.02-2.02 1.65-2.99 1.72-3.04-.94-1.37-2.4-1.56-2.92-1.58-1.24-.13-2.42.73-3.05.73-.63 0-1.6-.71-2.63-.69-1.35.02-2.6.79-3.29 2-1.4 2.43-.36 6.03 1 8 .67.97 1.46 2.05 2.5 2.01 1-.04 1.38-.65 2.59-.65 1.21 0 1.55.65 2.61.63 1.08-.02 1.76-.98 2.42-1.95.76-1.12 1.08-2.2 1.09-2.25-.02-.01-2.09-.8-2.11-3.19zM15.1 6.6c.55-.67.92-1.6.82-2.53-.79.03-1.75.53-2.32 1.2-.51.59-.96 1.54-.84 2.44.88.07 1.78-.45 2.34-1.11z"
        />
      </svg>
    )
  }

  if (name === 'github') {
    return (
      <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden focusable="false">
        <path
          fill="#181717"
          d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"
        />
      </svg>
    )
  }

  if (name === 'facebook') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden focusable="false">
        <path
          fill="#1877F2"
          d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.09 10.13 24v-8.44H7.08v-3.49h3.05V9.41c0-3.02 1.79-4.69 4.53-4.69 1.31 0 2.68.24 2.68.24v2.97h-1.51c-1.49 0-1.96.93-1.96 1.89v2.25h3.33l-.53 3.49h-2.8V24C19.61 23.09 24 18.1 24 12.07z"
        />
      </svg>
    )
  }

  // The university button is not a brand we're borrowing, so unlike the rest
  // this one is ours and follows the theme.
  if (name === 'university') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="#1f1f1f"
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
        focusable="false"
      >
        <path d="M12 3 2 8l10 5 10-5-10-5z" />
        <path d="M6 10.5V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-5.5" />
      </svg>
    )
  }

  // An unknown provider still gets a button, just without a logo -- better than
  // the button vanishing because the server offered something we don't draw.
  return null
}
