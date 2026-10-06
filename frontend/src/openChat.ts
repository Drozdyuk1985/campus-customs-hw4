// Open the chat panel from anywhere on the page (e.g. "Ask about this product"),
// optionally with a question already typed in for the customer to edit or send.
export const OPEN_CHAT_EVENT = 'cc:open-chat'

export function openChat(prefill?: string) {
  window.dispatchEvent(new CustomEvent(OPEN_CHAT_EVENT, { detail: { prefill } }))
}
