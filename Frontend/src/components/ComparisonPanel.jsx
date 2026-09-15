export default function ComparisonPanel({ comparison, notice }) {
  if (!comparison) return <p className="text-gray-300 rounded-xl border border-blue-500/20 p-4">{notice}</p>;
  const c = comparison;
  return <section aria-label="Before and after accessibility comparison" className="bg-gray-800/50 border border-blue-500/20 rounded-2xl p-6 space-y-6">
    <h3 className="text-2xl font-bold text-blue-400">Before / After Accessibility</h3>
    <div className="grid grid-cols-2 gap-4">
      {['Before', 'After'].map(label => <div key={label} className="min-w-0 rounded-xl bg-gray-900/50 p-4">
        <p className="text-gray-300 break-words">{label} · {new Date(c[`${label.toLowerCase()}Date`]).toLocaleString()}</p>
        <p className="text-4xl text-white font-bold my-2">{c[`${label.toLowerCase()}Score`]}<span className="text-base text-gray-400"> / 100</span></p>
        <progress aria-label={`${label} accessibility score`} className="w-full accent-blue-500" value={c[`${label.toLowerCase()}Score`]} max="100" />
      </div>)}
    </div>
    <p className={`text-xl font-semibold ${c.scoreChange > 0 ? 'text-green-400' : c.scoreChange < 0 ? 'text-red-400' : 'text-gray-300'}`}>
      {c.scoreChange > 0 ? '+' : ''}{c.scoreChange} points · {c.scoreChange > 0 ? 'Improved' : c.scoreChange < 0 ? 'Decreased' : 'Unchanged'}
    </p>
    <table className="w-full text-left text-gray-300">
      <caption className="sr-only">Violation occurrences before and after</caption>
      <thead><tr><th scope="col">Violations</th><th scope="col">Before</th><th scope="col">After</th><th scope="col">Change</th></tr></thead>
      <tbody>{[['Total', { before: c.beforeTotal, after: c.afterTotal }], ...Object.entries(c.severities)].map(([severity, counts]) =>
        <tr key={severity} className="border-t border-gray-700"><th scope="row" className="py-3 capitalize">{severity}</th><td>{counts.before}</td><td>{counts.after}</td>
          <td>{counts.after < counts.before ? 'Improved' : counts.after > counts.before ? 'Increased' : 'Unchanged'}</td></tr>)}</tbody>
    </table>
    <div className="grid sm:grid-cols-3 gap-4">{[['resolved', 'Resolved'], ['remaining', 'Remaining'], ['new', 'Newly detected']].map(([key, title]) =>
      <div key={key} className="p-4 rounded-xl bg-gray-900/40"><h4 className="text-blue-300 font-semibold">{title} ({c[key].length})</h4>
        <ul className="text-gray-300 mt-2 space-y-2">{c[key].length ? c[key].map(issue => <li key={issue.rule_id}>{issue.title} <span className="text-xs">({issue.rule_id})</span></li>) : <li>None</li>}</ul>
      </div>)}</div>
    <p className="text-gray-300">{c.summary}</p><p className="text-sm text-gray-400">{notice}</p>
  </section>;
}
