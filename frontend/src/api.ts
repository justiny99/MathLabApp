export type Textbook = {
  id: string
  title: string
  subject: string
  source_url: string | null
  ingest_status: string
  is_fixture: boolean
}

export type Health = {
  ok: boolean
  ollama: {
    reachable: boolean
    chat_model: string
    embed_model: string
    chat_model_present: boolean
    embed_model_present: boolean
  }
}

export type Question = {
  id: string
  source: 'extracted' | 'generated'
  textbook_id: string | null
  subject: string | null
  section: string | null
  stem_md: string
  has_official_answer: boolean
}

export type Grade = {
  correct: boolean
  feedback_md: string
  solution_md: string | null
}

export type ChatMessage = {
  role: 'user' | 'assistant' | 'system'
  content: string
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string }
    if (typeof data.detail === 'string') return data.detail
  } catch {
    /* ignore */
  }
  return res.statusText
}

export async function getHealth(): Promise<Health> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function getSubjects(): Promise<string[]> {
  const res = await fetch('/api/subjects')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function getTextbooks(subject?: string): Promise<Textbook[]> {
  const qs = subject ? `?subject=${encodeURIComponent(subject)}` : ''
  const res = await fetch(`/api/textbooks${qs}`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function nextQuestion(opts: {
  subject?: string
  textbookId?: string
  exclude: string[]
  generate?: boolean
}): Promise<Question> {
  const params = new URLSearchParams()
  if (opts.subject) params.set('subject', opts.subject)
  if (opts.textbookId) params.set('textbook_id', opts.textbookId)
  if (opts.exclude.length) params.set('exclude', opts.exclude.join(','))
  if (opts.generate) params.set('generate', 'true')
  const res = await fetch(`/api/questions/next?${params.toString()}`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function gradeQuestion(body: {
  question_id: string
  work: string
  source: Question['source']
}): Promise<Grade> {
  const res = await fetch('/api/grade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function sendChat(body: {
  messages: ChatMessage[]
  textbook_id?: string
  subject?: string
  question_id?: string
  work?: string
  submitted?: boolean
}): Promise<{ reply: string; used_chunks: number }> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
