export default function IssueExplanation({ issue }) {
  const e = issue.explanation;
  if (!e) return null;
  return <div className="space-y-4 text-gray-300">
    <div><h5 className="text-blue-400 font-semibold">Why it matters</h5><p>{e.why_it_matters}</p></div>
    <div><h5 className="text-blue-400 font-semibold">Who may be affected</h5><p>{e.affected_users.join(', ')}</p></div>
    <div><h5 className="text-blue-400 font-semibold">WCAG</h5><p>{e.wcag_criteria.length ? issue.wcagReference : 'No confidently matched WCAG criterion.'}</p></div>
    <div><h5 className="text-blue-400 font-semibold">Detected evidence</h5>
      {issue.detected_evidence.map((node, i) => <details key={i} className="my-2 rounded-lg bg-gray-900/50 p-3">
        <summary className="cursor-pointer focus-ring break-all">{node.target.flat(Infinity).join(' → ')}</summary>
        <pre className="whitespace-pre-wrap break-words text-sm mt-2">{node.html}{'\n'}{node.failureSummary}</pre>
        {node.checks?.filter(check => check.data).map((check, n) => <pre key={n} className="whitespace-pre-wrap break-words text-xs mt-2">{check.id}: {JSON.stringify(check.data, null, 2)}</pre>)}
      </details>)}
    </div>
    <div><h5 className="text-blue-400 font-semibold">Why this recommendation helps</h5><p>{e.reasoning_summary}</p></div>
    <div><h5 className="text-blue-400 font-semibold">Recommendation confidence: {e.confidence} ({e.confidence_score}/100)</h5><p className="text-sm">{e.confidence_basis}</p></div>
    {e.ai_summary && <div><h5 className="text-blue-400 font-semibold">AI-selected supporting evidence</h5><p className="whitespace-pre-wrap">{e.ai_summary}</p></div>}
    <div><h5 className="text-blue-400 font-semibold">Sources</h5>
      {e.evidence.map((source, i) => <details key={i} className="my-2"><summary className="cursor-pointer focus-ring">WCAG {source.version} · {source.criterion} · Level {source.level}{!source.criterion_match && ' (related guidance only)'}</summary>
        <p className="my-2">{source.text}</p><a className="text-blue-300 underline" href={source.source} target="_blank" rel="noreferrer">Read W3C source: {source.title}</a>
      </details>)}
      {issue.helpUrl && <a className="text-blue-300 underline" href={issue.helpUrl} target="_blank" rel="noreferrer">axe rule documentation</a>}
    </div><p className="text-sm text-gray-400">{e.status}</p>
  </div>;
}
