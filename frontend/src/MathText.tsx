import katex from 'katex'
import { Fragment, type ReactNode } from 'react'

const TOKEN = /(\$\$[\s\S]+?\$\$|\$[^$\n]+\$)/g

function renderMath(expr: string, display: boolean): string {
  return katex.renderToString(expr, {
    displayMode: display,
    throwOnError: false,
  })
}

export function MathText({ text }: { text: string }) {
  const nodes: ReactNode[] = []
  let last = 0
  let key = 0
  const re = new RegExp(TOKEN.source, 'g')
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(<Fragment key={key++}>{text.slice(last, match.index)}</Fragment>)
    }
    const token = match[0]
    const display = token.startsWith('$$')
    const expr = display ? token.slice(2, -2) : token.slice(1, -1)
    nodes.push(
      <span
        key={key++}
        className={display ? 'math-block' : 'math-inline'}
        dangerouslySetInnerHTML={{ __html: renderMath(expr, display) }}
      />,
    )
    last = match.index + token.length
  }
  if (last < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>)
  }
  return <div className="math-text">{nodes}</div>
}
