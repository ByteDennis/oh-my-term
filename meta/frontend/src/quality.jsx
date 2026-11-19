import React, {Fragment, useEffect, useState} from 'react';
import {ChevronDown, ChevronRight, Info, Search} from 'lucide-react';

export const rowCount = number => number == null ? '—' : number.toLocaleString('en-US');
export const percent = number => number == null ? '—' : `${number.toFixed(2)}%`;
const statusName = status => ({passed: 'Passed', failed: 'Failed', warning: 'Warning', not_evaluated: 'Not evaluated'}[status] || status);

export function useQuality(assetId) {
  const [state, setState] = useState({data: null, error: '', loading: true});
  useEffect(() => {
    if (!assetId) return;
    let active = true;
    setState({data: null, error: '', loading: true});
    fetch(`/api/assets/${encodeURIComponent(assetId)}/quality`).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Unable to load quality results');
      if (active) setState({data: body, error: '', loading: false});
    }).catch(error => {if (active) setState({data: null, error: error.message, loading: false});});
    return () => {active = false;};
  }, [assetId]);
  return state;
}

export default function QualityPanel({quality}) {
  const [snapshot, setSnapshot] = useState(''), [severity, setSeverity] = useState('all');
  const [result, setResult] = useState('all'), [query, setQuery] = useState(''), [expanded, setExpanded] = useState('');
  const data = quality.data;
  const runs = data?.runs || [];
  const run = runs.find(item => item.snapshot_id === snapshot) || runs[0];
  const checks = run?.checks || [];
  const filtered = checks.filter(check => (severity === 'all' || check.criticality === severity)
    && (result === 'all' || (result === 'issues' ? ['failed', 'warning'].includes(check.status) : check.status === result))
    && `${check.name} ${check.columns.join(' ')} ${check.dimension || ''}`.toLowerCase().includes(query.toLowerCase()));
  if (quality.loading) return <p className="muted">Loading quality results…</p>;
  if (quality.error) return <p className="error" role="alert">{quality.error}</p>;
  if (!run) return <div className="quality-empty"><h2>Quality results</h2><p className="muted">No recorded DQX runs for this table.</p><p className="footnote">No result is different from a passing result.</p></div>;
  return <div className="quality-report">
    <div className="quality-heading"><h2>Quality results</h2>
      <div className="quality-run-picker"><span className="pill sample">{data.sample_data ? 'Preview results' : 'Recorded results'}</span><select aria-label="Quality run" value={run.snapshot_id} onChange={e => {setSnapshot(e.target.value); setExpanded('');}}>
        {runs.map((item, i) => <option key={item.snapshot_id} value={item.snapshot_id}>{item.run_time.slice(0, 10)} · {item.run_time.slice(11, 16)} UTC{i === 0 ? ' · latest' : ''}</option>)}
      </select></div>
    </div>
    <div className="quality-stats" aria-label="Run summary">
      <div><span>Valid rows</span><strong>{percent(run.valid_row_rate)}</strong><small>{rowCount(run.valid_row_count)} without issues</small></div>
      <div><span>Input rows</span><strong>{rowCount(run.input_row_count)}</strong></div>
      <div className={run.error_row_count ? 'stat-error' : ''}><span>Error rows</span><strong>{rowCount(run.error_row_count)}</strong></div>
      <div className={run.warning_row_count ? 'stat-warning' : ''}><span>Warning rows</span><strong>{rowCount(run.warning_row_count)}</strong></div>
      <div><span>Checks passed</span><strong>{run.per_check_available ? checks.filter(check => check.status === 'passed').length : '—'}{run.per_check_available && <em> / {checks.length}</em>}</strong><small>{run.per_check_available ? `${checks.filter(check => ['failed', 'warning'].includes(check.status)).length} with issues` : 'Breakdown unavailable'}</small></div>
    </div>
    <div className="quality-context"><span><Info size={13}/> Error and warning rows may overlap.</span><details><summary>Metric definitions<ChevronDown size={12}/></summary><p>Valid rows pass all checks with no errors or warnings. Valid % = valid / input; this is not DQX Studio’s average check pass score. A check’s pass rate uses its own checked-row count. Zero checked rows means not evaluated, not passed.</p></details></div>
    <div className="quality-controls"><label className="quality-search"><Search size={14}/><input aria-label="Search quality checks" placeholder="Find a check or attribute" value={query} onChange={e => setQuery(e.target.value)}/></label>
      <select aria-label="Quality severity" value={severity} onChange={e => setSeverity(e.target.value)}><option value="all">All severities</option><option value="error">Error</option><option value="warn">Warn</option></select>
      <select aria-label="Quality result" value={result} onChange={e => setResult(e.target.value)}><option value="all">All results</option><option value="issues">Issues only</option><option value="passed">Passed</option><option value="not_evaluated">Not evaluated</option></select>
      <span className="muted">{filtered.length} of {checks.length} checks</span>
    </div>
    {!run.per_check_available && <p className="notice">Per-check metrics were not captured for this run. They require DQX Core check_metrics output; missing results are not counted as passing.</p>}
    <div className="table-scroll"><table className="quality-table"><thead><tr><th>Check / attribute</th><th>Severity</th><th>Checked rows</th><th>Issue rows</th><th>Pass rate</th><th>Result</th></tr></thead><tbody>
      {filtered.map(check => <Fragment key={check.rule_fingerprint}><tr>
        <td><button className="quality-check-button" aria-label={`View check ${check.name}`} aria-expanded={expanded === check.rule_fingerprint} onClick={() => setExpanded(expanded === check.rule_fingerprint ? '' : check.rule_fingerprint)}><ChevronRight size={13} className={expanded === check.rule_fingerprint ? 'open' : ''}/><span>{check.name}<small>{check.columns.length ? check.columns.join(', ') : 'Attribute metadata unavailable'}</small></span></button></td>
        <td><span className={`pill ${check.criticality === 'warn' ? 'warning' : ''}`}>{check.criticality === 'warn' ? 'Warn' : check.criticality === 'error' ? 'Error' : 'Unknown'}</span></td>
        <td className="numeric">{rowCount(check.checked_count)}</td><td className={`numeric ${check.failed_count ? 'has-issues' : ''}`}>{rowCount(check.failed_count)}</td><td className="numeric">{percent(check.pass_rate)}</td><td><span className={`pill ${check.status}`}>{statusName(check.status)}</span></td>
      </tr>{expanded === check.rule_fingerprint && <tr className="quality-detail"><td colSpan="6"><div className="quality-check-details">
        <div><span className="detail-label">Recorded rule</span><code>{check.rule || (check.function ? `${check.function}(${JSON.stringify(check.arguments)})` : 'Rule definition was not captured for this run.')}</code>
          <span className="muted">{check.dimension || 'Dimension not recorded'} · Filter: {check.filter || 'All input rows'}</span>
          {check.checked_count === 0 && <p className="muted">No rows were evaluated. Reported issue flags may describe a skipped check; no pass rate is calculated.</p>}
        </div><div><span className="detail-label">Run</span><code>{run.run_id}</code><span className="muted">{run.run_time.replace('T', ' ').replace('Z', ' UTC')}</span><code>{run.input_location}</code></div>
        <details><summary>Traceability<ChevronDown size={12}/></summary><div>Rule fingerprint <code>{check.rule_fingerprint}</code></div><div>Rule-set fingerprint <code>{run.rule_set_fingerprint || 'Not captured'}</code></div><p className="muted">Definitions are matched to this recorded rule set. Raw failing records are not loaded in this prototype.</p></details>
      </div></td></tr>}</Fragment>)}
      {!filtered.length && <tr><td colSpan="6" className="empty">{checks.length ? 'No checks match these filters.' : 'No per-check breakdown is available.'}</td></tr>}
    </tbody></table></div>
    <details className="quality-history"><summary>Valid rows · last {Math.min(runs.length, 7)} runs<ChevronDown size={12}/></summary><div className="quality-history-values">{runs.slice(0, 7).reverse().map(item => <button key={item.snapshot_id} aria-label={`Select quality run ${item.run_time.slice(0, 10)}`} className={item.snapshot_id === run.snapshot_id ? 'selected' : ''} onClick={() => {setSnapshot(item.snapshot_id); setExpanded('');}}><small>{item.run_time.slice(5, 10)}</small><strong>{percent(item.valid_row_rate)}</strong></button>)}</div></details>
    <div className="quality-source"><span className="pill sample">{{not_connected: 'Not connected', synced: 'Synced', failed: 'Sync failed', stale: 'Stale snapshot'}[data.sync_status] || 'Sync status unknown'}</span><span>DQX Core metrics</span><span>Last sync: {data.last_synced_at ? data.last_synced_at.replace('T', ' ').replace('Z', ' UTC') : '—'}</span></div>
  </div>;
}
