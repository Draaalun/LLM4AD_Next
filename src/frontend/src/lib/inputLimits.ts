/**
 * Centralized character limits for free-text inputs that use native
 * `<input>` / `<textarea>` elements (i.e. those that bypass the shared
 * `Input` / `Textarea` UI components, which already enforce their own
 * `maxLength` defaults of 256 / 2000).
 *
 * Tune these in one place rather than sprinkling magic numbers across the app.
 */
export const INPUT_LIMITS = {
  /** Chat composer message (AI build / chat-tune). Generous but bounded. */
  chatMessage: 8000,
  /** Free-text answers in interactive assistant cards. */
  cardText: 2000,
  /** Search boxes (logs, version tree, etc.). */
  search: 200,
  /** Short identifiers: model names, tags, rename fields. */
  name: 200,
} as const
