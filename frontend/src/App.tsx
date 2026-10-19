import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  getHealth,
  getSubjects,
  getTextbooks,
  gradeQuestion,
  nextQuestion,
  sendChat,
  type ChatMessage,
  type Grade,
  type Health,
  type Question,
  type Textbook,
} from './api'
import { MathText } from './MathText'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [subjects, setSubjects] = useState<string[]>([])
  const [textbooks, setTextbooks] = useState<Textbook[]>([])
  const [subject, setSubject] = useState('')
  const [textbookId, setTextbookId] = useState('')
  const [question, setQuestion] = useState<Question | null>(null)
  const [seen, setSeen] = useState<string[]>([])
  const [work, setWork] = useState('')
  const [grade, setGrade] = useState<Grade | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [chatBusy, setChatBusy] = useState(false)

  const ollamaReady = Boolean(health?.ollama.reachable)

  const loadMeta = useCallback(async () => {
    try {
      const [h, s] = await Promise.all([getHealth(), getSubjects()])
      setHealth(h)
      setSubjects(s)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    void loadMeta()
  }, [loadMeta])

  useEffect(() => {
    void getTextbooks(subject || undefined).then(setTextbooks).catch((err) => {
      setError(err instanceof Error ? err.message : String(err))
    })
  }, [subject])

  const filteredBooks = useMemo(() => textbooks, [textbooks])

  async function loadQuestion(generate = false) {
    setBusy(true)
    setError(null)
    setGrade(null)
    setWork('')
    try {
      const q = await nextQuestion({
        subject: subject || undefined,
        textbookId: textbookId || undefined,
        exclude: seen,
        generate,
      })
      setQuestion(q)
      setSeen((prev) => (prev.includes(q.id) ? prev : [...prev, q.id]))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit() {
    if (!question) return
    setBusy(true)
    setError(null)
    try {
      const result = await gradeQuestion({
        question_id: question.id,
        work,
        source: question.source,
      })
      setGrade(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
    // Reset to allow user to continue working
  }

  async function onChat(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim()) return
    const next: ChatMessage[] = [...chat, { role: 'user', content: draft.trim() }]
    setChat(next)
    setDraft('')
    setChatBusy(true)
    try {
      const { reply } = await sendChat({
        messages: next,
        textbook_id: textbookId || question?.textbook_id || undefined,
        subject: subject || question?.subject || undefined,
        question_id: question?.id,
        work,
        submitted: Boolean(grade),
      })
      setChat([...next, { role: 'assistant', content: reply }])
    } catch (err) {
      setChat([
        ...next,
        {
          role: 'assistant',
          content: err instanceof Error ? err.message : String(err),
        },
      ])
    } finally {
      setChatBusy(false)
    }
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>MathProblemApp</h1>
          <p className="muted">Practice from extracted textbook exercises, with local RAG help.</p>
        </div>
        <div className={`pill ${ollamaReady ? 'ok' : 'down'}`}>
          {ollamaReady
            ? `Ollama ${health?.ollama.chat_model}`
            : 'Ollama offline'}
        </div>
      </header>

      <section className="controls">
        <label>
          Subject
          <select
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value)
              setTextbookId('')
              setSeen([])
              setQuestion(null)
              setGrade(null)
            }}
          >
            <option value="">All subjects</option>
            {subjects.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Textbook
          <select
            value={textbookId}
            onChange={(e) => {
              setTextbookId(e.target.value)
              setSeen([])
              setQuestion(null)
              setGrade(null)
            }}
          >
            <option value="">Any matching book</option>
            {filteredBooks.map((book) => (
              <option key={book.id} value={book.id}>
                {book.title}
                {book.ingest_status !== 'ingested' ? ` (${book.ingest_status})` : ''}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void loadQuestion(false)} disabled={busy}>
          {question ? 'Next question' : 'Start'}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => void loadQuestion(true)}
          disabled={busy || !ollamaReady}
        >
          Generate similar
        </button>
      </section>

      {error ? <p className="banner error">{error}</p> : null}
      {!ollamaReady ? (
        <p className="banner warn">
          Chat, generated questions, and LLM grading need a local Ollama server. Extracted
          fixture problems still work for matching answers.
        </p>
      ) : null}

      <div className="layout">
        <main className="panel">
          {!question ? (
            <p className="muted">Choose a subject or textbook, then start. The fixture algebra book is included.</p>
          ) : (
            <>
              <div className="meta">
                <span>{question.source === 'extracted' ? 'From textbook' : 'Generated'}</span>
                {question.section ? <span>{question.section}</span> : null}
                {question.subject ? <span>{question.subject}</span> : null}
              </div>
              <MathText text={question.stem_md} />
              <label className="work">
                Your work
                <textarea
                  value={work}
                  onChange={(e) => setWork(e.target.value)}
                  rows={8}
                  placeholder="Write the solution or final answer…"
                />
              </label>
              <button type="button" onClick={() => void onSubmit()} disabled={busy || !work.trim()}>
                Submit
              </button>
              {grade ? (
                <div className={`result ${grade.correct ? 'ok' : 'no'}`}>
                  <strong>{grade.correct ? 'Correct' : 'Not quite'}</strong>
                  <MathText text={grade.feedback_md} />
                  {grade.solution_md ? (
                    <>
                      <h3>Solution</h3>
                      <MathText text={grade.solution_md} />
                    </>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
        </main>

        <aside className="panel chat">
          <h2>Tutor</h2>
          <p className="muted">Local Ollama with RAG over ingested chapter text.</p>
          <div className="thread">
            {chat.length === 0 ? (
              <p className="muted">Ask about a stuck step. The tutor stays scoped to your current book/problem.</p>
            ) : (
              chat.map((msg, i) => (
                <div key={`${msg.role}-${i}`} className={`msg ${msg.role}`}>
                  <span className="who">{msg.role === 'user' ? 'You' : 'Tutor'}</span>
                  <MathText text={msg.content} />
                </div>
              ))
            )}
          </div>
          <form onSubmit={onChat} className="composer">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={ollamaReady ? 'Where do I start?' : 'Ollama is offline'}
              disabled={!ollamaReady || chatBusy}
            />
            <button type="submit" disabled={!ollamaReady || chatBusy || !draft.trim()}>
              Send
            </button>
          </form>
        </aside>
      </div>
    </div>
  )
}
