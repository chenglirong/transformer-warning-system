import http from './http'

export async function chatAssistant(message, { sessionId = null, selectedDate = null, forceTemplate = false } = {}) {
  return http.post('/assistant/chat', {
    message,
    session_id: sessionId,
    selected_date: selectedDate,
    force_template: forceTemplate,
  })
}

export async function getAssistantSuggestions() {
  return http.get('/assistant/suggestions')
}

export async function syncAssistant({ sessionId = null, day, result } = {}) {
  return http.post('/assistant/sync', {
    session_id: sessionId,
    day,
    result,
  })
}
