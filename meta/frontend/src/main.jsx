import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Database, Search, ChevronRight, ChevronDown, X, ShieldCheck, BookOpen,
  GitBranch, Table2, Activity, Users, Link2, Pencil, Plus, Trash2, Layers3, LogOut, Copy} from 'lucide-react';
import './style.css';
import QualityPanel, {useQuality, percent} from './quality';

async function api(path, options = {}) {
  const response = await fetch('/api' + path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  const body = await response.json();
  if (!response.ok) {
    const message = Array.isArray(body.detail) ? body.detail.map(x => `${x.loc.slice(1).join('.')}: ${x.msg}`).join('; ') : body.detail;
    throw new Error(message || 'Request failed. Please try again.');
  }
  return body;
}

const tabs = [['overview', 'Overview', BookOpen], ['fields', 'Attributes', Table2], ['lineage', 'Lineage', GitBranch],
  ['quality', 'Quality', Activity], ['impact', 'Impact', Layers3]];
const title = asset => `${asset.schema_name}.${asset.name}`;
const blankContact = () => ({team: '', name: '', email: ''});
const Pill = ({children, tone = ''}) => <span className={`pill ${tone}`}>{children}</span>;
const formatTime = value => value ? new Date(value).toLocaleString('en-US', {
  year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
}) : '—';

function Modal({title, onClose, children, wide = false}) {
  const ref = useRef();
  useEffect(() => {const dialog = ref.current; dialog.showModal(); return () => dialog.close();}, []);
  return <dialog ref={ref} className={wide ? 'wide' : ''} onCancel={event => {event.preventDefault(); onClose();}}>
    <header className="modal-head"><h2>{title}</h2><button className="icon" aria-label="Close dialog" onClick={onClose}><X size={20}/></button></header>
    {children}
  </dialog>;
}

function Login({onClose, onLogin, enabled}) {
  const [password, setPassword] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  return <Modal title="Admin sign-in" onClose={onClose}><form className="modal-body" onSubmit={async event => {
    event.preventDefault(); setBusy(true); setError('');
    try {await api('/auth/login', {method: 'POST', body: JSON.stringify({password})}); await onLogin();}
    catch (error) {setError(error.message);} finally {setBusy(false);}
  }}>
    <p className="muted">Readers can explore all metadata. Admins can update definitions, relationships, checks, and contacts.</p>
    {!enabled && <p className="notice">Admin editing has not been configured on this server. Browsing is available.</p>}
    <label>Admin password<input type="password" autoComplete="current-password" autoFocus value={password} onChange={e => setPassword(e.target.value)} required disabled={!enabled}/></label>
    {error && <p className="error" role="alert">{error}</p>}
    <button className="primary" disabled={busy || !enabled}>{busy ? 'Signing in…' : 'Sign in'}</button>
  </form></Modal>;
}

function EditAsset({asset, assets, onClose, onSave}) {
  const [draft, setDraft] = useState(() => structuredClone(asset)), [section, setSection] = useState('Details');
  const [error, setError] = useState(''), [saving, setSaving] = useState(false);
  const change = fn => setDraft(old => {const next = structuredClone(old); fn(next); return next;});
  const input = (label, value, set, multiline = false) => <label>{label}{multiline
    ? <textarea value={value} onChange={e => set(e.target.value)} rows={3}/>
    : <input value={value} onChange={e => set(e.target.value)} required/>}</label>;
  const people = (key, label) => <section><div className="section-line"><h3>{label}</h3><button type="button" onClick={() => change(d => d[key].push(blankContact()))}><Plus size={15}/> Add contact</button></div>
    {draft[key].map((person, i) => <div className="edit-person" key={i}>
      {input('Team', person.team, value => change(d => d[key][i].team = value))}
      {input('Name', person.name, value => change(d => d[key][i].name = value))}
      {input('Email', person.email, value => change(d => d[key][i].email = value))}
      <button type="button" className="icon danger" aria-label={`Remove ${label} contact ${i + 1}`} onClick={() => change(d => d[key].splice(i, 1))}><Trash2 size={17}/></button>
    </div>)}
  </section>;
  return <Modal title={`Edit ${title(asset)}`} onClose={onClose} wide>
    <div className="edit-tabs">{['Details', 'Attributes', 'Quality'].map(name => <button key={name} className={section === name ? 'selected' : ''} onClick={() => setSection(name)}>{name}</button>)}</div>
    <form onSubmit={async event => {event.preventDefault(); setSaving(true); setError('');
      try {const updated = await api(`/assets/${asset.id}`, {method: 'PUT', body: JSON.stringify(draft)}); onSave(updated);}
      catch (error) {setError(error.message);} finally {setSaving(false);}
    }}>
      <div className="editor-content">
        {section === 'Details' && <>
          <div className="form-grid">{input('Table name', draft.name, value => change(d => d.name = value))}{input('Schema', draft.schema_name, value => change(d => d.schema_name = value))}
            {input('Domain', draft.domain, value => change(d => d.domain = value))}{input('Owner team', draft.owner, value => change(d => d.owner = value))}</div>
          {input('Business definition', draft.description, value => change(d => d.description = value), true)}
          {people('contacts', 'Owner contacts')}{people('consumers', 'Business consumers')}
        </>}
        {section === 'Attributes' && <>
          <div className="section-line"><p className="muted">Definitions, transformations, and source attributes.</p><button type="button" onClick={() => change(d => d.columns.push({name: `new_column_${d.columns.length + 1}`, data_type: 'VARCHAR', definition: '', transformation: '', sources: []}))}><Plus size={15}/> Add attribute</button></div>
          {draft.columns.map((column, i) => <details className="edit-block" key={i} open={undefined}><summary>{column.name}<ChevronDown size={16}/></summary><div className="edit-block-body">
            <div className="form-grid">{input('Attribute name', column.name, value => change(d => d.columns[i].name = value))}{input('Data type', column.data_type, value => change(d => d.columns[i].data_type = value))}</div>
            {input('Business definition', column.definition, value => change(d => d.columns[i].definition = value), true)}
            {input('Transformation', column.transformation, value => change(d => d.columns[i].transformation = value), true)}
            <div className="section-line"><h4>Source attributes</h4><button type="button" onClick={() => change(d => d.columns[i].sources.push({table: assets[0].id, column: assets[0].columns[0]?.name || ''}))}><Plus size={14}/> Add source</button></div>
            {column.sources.map((source, j) => <div className="source-edit" key={j}><label>Source table<select value={source.table} onChange={e => {const table = assets.find(a => a.id === e.target.value); change(d => d.columns[i].sources[j] = {table: table.id, column: table.columns[0]?.name || ''});}}>{assets.map(a => <option value={a.id} key={a.id}>{title(a)}</option>)}</select></label>
              <label>Source attribute<select value={source.column} onChange={e => change(d => d.columns[i].sources[j].column = e.target.value)}>{assets.find(a => a.id === source.table)?.columns.map(c => <option key={c.name}>{c.name}</option>)}</select></label>
              <button type="button" className="icon" aria-label="Remove source" onClick={() => change(d => d.columns[i].sources.splice(j, 1))}><X size={16}/></button></div>)}
            <button type="button" className="danger" onClick={() => change(d => d.columns.splice(i, 1))}><Trash2 size={14}/> Remove attribute</button>
          </div></details>)}
        </>}
        {section === 'Quality' && <>
          <p className="notice">Edit curated check definitions here. The Quality report shows recorded DQX run metrics; no database checks or scheduled jobs run in this prototype.</p>
          {draft.checks.map((check, i) => <details className="edit-block" key={i}><summary>{check.name}<ChevronDown size={16}/></summary><div className="edit-block-body">
            {input('Check name', check.name, value => change(d => d.checks[i].name = value))}
            <label>Attribute<select value={check.column} onChange={e => change(d => d.checks[i].column = e.target.value)}><option value="">Whole table</option>{draft.columns.map(c => <option key={c.name}>{c.name}</option>)}</select></label>
            {input('Rule', check.rule, value => change(d => d.checks[i].rule = value), true)}
            <button type="button" className="danger" onClick={() => change(d => d.checks.splice(i, 1))}><Trash2 size={14}/> Remove check</button>
          </div></details>)}
          <button type="button" onClick={() => change(d => d.checks.push({name: 'New check', column: '', rule: 'Define the rule', status: 'not_run', observed: '', checked_at: ''}))}><Plus size={15}/> Add check</button>
        </>}
      </div>
      <footer className="modal-foot">{error && <p className="error" role="alert">{error}</p>}<span className="muted">Revision {asset.version}</span><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button></footer>
    </form>
  </Modal>;
}

function EmailCopy({email, onCopy}) {
  return <button className="email-copy" aria-label={`Copy email address ${email}`} title="Copy email address" onClick={() => onCopy(email)}><Copy size={13}/><span>{email}</span></button>;
}

function Contacts({people, onCopy}) {
  if (!people.length) return <p className="muted">No contacts recorded.</p>;
  return <div className="people-grid">{people.map((person, index) => <div className="person" key={`${person.email}-${index}`}>
    <span className="avatar">{person.name.split(' ').map(s => s[0]).slice(0, 2).join('')}</span>
    <div><strong>{person.team}</strong><div className="muted">{person.name}</div><EmailCopy email={person.email} onCopy={onCopy}/></div>
  </div>)}</div>;
}

function Lineage({assets, selected, onSelect}) {
  const edges = [], nodes = new Map(assets.map(a => [a.id, a]));
  for (const asset of assets) for (const column of asset.columns) for (const source of column.sources)
    edges.push({from: source.table, to: asset.id, label: `${source.column} → ${column.name}`});
  const connected = new Set([selected]);
  for (let i = 0; i < assets.length; i++) for (const edge of edges) if (connected.has(edge.from) || connected.has(edge.to)) {connected.add(edge.from); connected.add(edge.to);}
  const visible = assets.filter(a => connected.has(a.id));
  const level = (id, seen = new Set()) => {
    if (seen.has(id)) return 0;
    const parents = edges.filter(e => e.to === id && nodes.has(e.from));
    return parents.length ? 1 + Math.max(...parents.map(e => level(e.from, new Set([...seen, id])))) : 0;
  };
  const groups = [];
  for (const asset of visible) {const depth = level(asset.id); (groups[depth] ||= []).push(asset);}
  const width = Math.max(groups.length * 294 + 20, 600), height = Math.max(...groups.map(g => g?.length || 0), 1) * 118 + 70;
  const positions = {};
  groups.forEach((group, x) => group.forEach((a, y) => positions[a.id] = {x: x * 294 + 24, y: (height - group.length * 118) / 2 + y * 118}));
  const uniqueEdges = [...new Set(edges.map(e => `${e.from}:${e.to}`))].map(key => edges.find(e => `${e.from}:${e.to}` === key));
  return <><div className="section-line"><div><h3>From source to business</h3><p className="muted">Select a table to explore its metadata.</p></div><Pill>{visible.length} connected tables</Pill></div>
    <div className="lineage-scroll"><svg className="lineage" viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Table lineage graph" style={{minWidth: Math.min(width, 860)}}>
      <defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#a7b3c8"/></marker></defs>
      {uniqueEdges.map(edge => {const a = positions[edge.from], b = positions[edge.to]; if (!a || !b) return null;
        return <path key={`${edge.from}-${edge.to}`} d={`M ${a.x + 236} ${a.y + 40} C ${a.x + 267} ${a.y + 40}, ${b.x - 30} ${b.y + 40}, ${b.x - 2} ${b.y + 40}`} fill="none" stroke="#a7b3c8" strokeWidth="1.5" markerEnd="url(#end)"><title>{edges.filter(e => e.from === edge.from && e.to === edge.to).map(e => e.label).join('\n')}</title></path>;
      })}
      {visible.map(asset => {const p = positions[asset.id]; return <g key={asset.id} role="button" tabIndex="0" aria-label={`Explore ${title(asset)}`} onClick={() => onSelect(asset.id)} onKeyDown={e => {if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); onSelect(asset.id);}}} className={asset.id === selected ? 'node current' : 'node'}>
        <rect x={p.x} y={p.y} width="236" height="80" rx="10"/><text x={p.x + 17} y={p.y + 25} className="node-schema">{asset.schema_name}</text><text x={p.x + 17} y={p.y + 49} className="node-name">{asset.name}</text><text x={p.x + 17} y={p.y + 67} className="node-meta">{asset.columns.length} attributes · {asset.domain}</text>
      </g>;})}
    </svg></div>
    <details className="mapping-details"><summary>Attribute mappings <ChevronDown size={16}/></summary>{edges.map((edge, i) => <div className="mapping" key={i}><code>{nodes.get(edge.from)?.name}.{edge.label.split(' → ')[0]}</code><ChevronRight size={14}/><code>{nodes.get(edge.to)?.name}.{edge.label.split(' → ')[1]}</code></div>)}</details>
  </>;
}

function App() {
  const [assets, setAssets] = useState([]), [session, setSession] = useState({role: 'reader'}), [assetId, setAssetId] = useState(location.hash.slice(1) || 'orders');
  const [query, setQuery] = useState(''), [domain, setDomain] = useState('All domains'), [tab, setTab] = useState('overview');
  const [column, setColumn] = useState(''), [impact, setImpact] = useState(null), [impactError, setImpactError] = useState('');
  const [tableDownstream, setTableDownstream] = useState({assetId: '', count: null});
  const [modal, setModal] = useState(''), [error, setError] = useState(''), [toast, setToast] = useState('');
  const search = useRef();
  const load = async () => {setError(''); try {const [data, role] = await Promise.all([api('/assets'), api('/session')]); setAssets(data); setSession(role);} catch (e) {setError(e.message);}};
  useEffect(() => {load(); const key = e => {if ((e.ctrlKey || e.metaKey) && e.key === 'k') {e.preventDefault(); search.current?.focus();}};
    const hash = () => {if (location.hash) {setAssetId(location.hash.slice(1)); setColumn('');}};
    window.addEventListener('keydown', key); window.addEventListener('hashchange', hash);
    return () => {window.removeEventListener('keydown', key); window.removeEventListener('hashchange', hash);};
  }, []);
  const asset = assets.find(a => a.id === assetId) || assets[0];
  const quality = useQuality(asset?.id);
  useEffect(() => {if (!asset) return; let live = true; setImpact(null); setImpactError('');
    api(`/assets/${asset.id}/impact${column ? '?column=' + encodeURIComponent(column) : ''}`).then(data => {if (live) {setImpact(data); if (!column) setTableDownstream({assetId: asset.id, count: data.downstream.length});}}).catch(e => {if (live) setImpactError(e.message);});
    return () => {live = false;};
  }, [asset, column]);
  useEffect(() => {if (toast) {const timer = setTimeout(() => setToast(''), 3500); return () => clearTimeout(timer);}}, [toast]);
  function select(id) {setAssetId(id); setColumn(''); history.replaceState({}, '', '#' + id);}
  async function copyEmail(email) {
    try {await navigator.clipboard.writeText(email); setToast('Email address copied');}
    catch {setToast('Unable to copy email address');}
  }
  const domains = ['All domains', ...new Set(assets.map(a => a.domain))];
  const filtered = assets.filter(a => (domain === 'All domains' || a.domain === domain) && `${title(a)} ${a.description} ${a.owner} ${a.columns.map(c => c.name + ' ' + c.definition).join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  const latestQuality = quality.data?.runs[0];
  return <div className="app">
    <header className="topbar"><a className="brand" href="#orders" onClick={() => select('orders')}><span className="brand-mark"><Layers3 size={19}/></span>Datasaurus<span className="brand-divider"/> <span className="brand-sub">Metadata workspace</span></a>
      <div className="top-actions">{session.role === 'admin'
        ? <><Pill tone="purple"><ShieldCheck size={13}/> Admin</Pill><button className="icon" aria-label="Sign out" onClick={async () => {try {await api('/auth/logout', {method: 'POST'}); setSession({...session, role: 'reader'}); setModal('');} catch (e) {setToast(e.message);}}}><LogOut size={17}/></button></>
        : session.admin_enabled && <button className="quiet" onClick={() => setModal('login')}><ShieldCheck size={15}/>Admin sign-in</button>}</div>
    </header>
    <aside className="sidebar"><div className="sidebar-title"><span>CATALOG</span><span>{assets.length} tables</span></div>
      <label className="search"><Search size={16}/><input ref={search} placeholder="Find a table or attribute" aria-label="Search catalog" value={query} onChange={e => setQuery(e.target.value)}/><kbd>⌘K</kbd></label>
      <label className="domain-filter"><select aria-label="Filter by domain" value={domain} onChange={e => setDomain(e.target.value)}>{domains.map(d => <option key={d}>{d}</option>)}</select></label>
      <nav className="asset-list" aria-label="Tables">{filtered.map(a => <button key={a.id} className={`asset-item ${asset?.id === a.id ? 'active' : ''}`} onClick={() => select(a.id)}><Table2 size={16}/><span><strong>{a.name}</strong><small>{a.schema_name} · {a.domain}</small></span>{asset?.id === a.id && <ChevronRight size={15}/>}</button>)}
        {!filtered.length && <p className="empty">No matching tables. Try a different search or domain.</p>}</nav>
      <label className="mobile-table-picker"><select aria-label="Choose table" value={filtered.some(a => a.id === asset?.id) ? asset.id : ''} onChange={e => select(e.target.value)}>
        <option value="" disabled>{filtered.length ? 'Choose a matching table' : 'No matching tables'}</option>{filtered.map(a => <option key={a.id} value={a.id}>{title(a)}</option>)}
      </select></label>
      <div className="sidebar-footer"><Database size={15}/><div>Catalog<small>{assets.length} tables · {domains.length - 1} domains</small></div></div>
    </aside>
    <main className={tab === 'quality' ? 'quality-main' : ''}>
      {error ? <div className="load-error" role="alert"><h2>Unable to load the catalog</h2><p>{error}</p><button onClick={load}>Try again</button></div> : !asset ? <div className="loading">Loading metadata…</div> : <>
        <div className="breadcrumbs">Catalog <ChevronRight size={13}/>{asset.schema_name}<ChevronRight size={13}/><span>{asset.name}</span></div>
        <div className="asset-heading"><div><div className="eyebrow"><Table2 size={14}/>TABLE<Pill>{asset.domain}</Pill></div><h1>{asset.name}</h1><code className="qualified">{title(asset)}</code></div>
          <div className="heading-actions"><button className="icon" aria-label="Copy table link" onClick={async () => {try {const url = new URL(location.href); url.hash = asset.id; await navigator.clipboard.writeText(url.href); setToast('Table link copied');} catch {setToast('Unable to copy the link');}}}><Link2 size={17}/></button>
            {session.role === 'admin' && <button onClick={() => setModal('edit')}><Pencil size={15}/>Edit metadata</button>}</div>
        </div>
        <div className="asset-meta"><details className="owner-menu" key={asset.id}><summary><Users size={13}/><span>Owner: {asset.owner}</span><ChevronDown size={12}/></summary><div className="owner-popover"><Contacts people={asset.contacts} onCopy={copyEmail}/></div></details><span>{asset.columns.length} attributes</span><span>{tableDownstream.assetId === asset.id ? tableDownstream.count : '…'} downstream tables</span><span>Revision {asset.version}</span></div>
        <div className="tabs" role="tablist" aria-label="Metadata sections">{tabs.map(([id, name, Icon], i) => <button role="tab" id={`tab-${id}`} aria-controls="metadata-panel" aria-selected={tab === id} tabIndex={tab === id ? 0 : -1} key={id} onClick={() => setTab(id)} onKeyDown={e => {
          let next; if (e.key === 'ArrowRight') next = (i + 1) % tabs.length; if (e.key === 'ArrowLeft') next = (i + tabs.length - 1) % tabs.length; if (e.key === 'Home') next = 0; if (e.key === 'End') next = tabs.length - 1;
          if (next !== undefined) {e.preventDefault(); setTab(tabs[next][0]); document.getElementById(`tab-${tabs[next][0]}`).focus();}
        }}><Icon size={16}/>{name}{id === 'fields' && <span className="tab-count">{asset.columns.length}</span>}</button>)}</div>
        <section className="panel" role="tabpanel" id="metadata-panel" aria-labelledby={`tab-${tab}`}>
          {tab === 'overview' && <>
            <div className="section-line"><h2>Business definition</h2><Pill tone="purple">Curated</Pill></div><p className="definition">{asset.description || 'No business definition has been added yet.'}</p>
            <div className="overview-grid"><section className="card"><div className="card-heading"><Users size={17}/><h3>Used by</h3><span>{asset.consumers.length} teams</span></div>{asset.consumers.length ? asset.consumers.map((c, i) => <div className="consumer" key={i}><span className="mini-avatar">{c.team[0]}</span><div><strong>{c.team}</strong><small>{c.name}</small></div></div>) : <p className="muted">No business consumers recorded.</p>}</section>
              <section className="card"><div className="card-heading"><Activity size={17}/><h3>Quality snapshot</h3><Pill tone="sample">{quality.data?.sample_data ? 'Preview' : 'Results'}</Pill></div><div className="quality-score"><strong>{latestQuality ? percent(latestQuality.valid_row_rate) : '—'}</strong><span>{quality.loading ? 'Loading results' : quality.error ? 'Results unavailable' : latestQuality ? 'valid rows' : 'No recorded results'}</span></div><div className="quality-bar"><span style={{width: latestQuality?.valid_row_rate != null ? `${latestQuality.valid_row_rate}%` : '0%'}}/></div><button className="text-button" onClick={() => setTab('quality')}>View quality results <ChevronRight size={15}/></button></section></div>
            <details className="mapping-details"><summary>At a glance<ChevronDown size={16}/></summary><dl className="glance"><div><dt>Schema</dt><dd>{asset.schema_name}</dd></div><div><dt>Domain</dt><dd>{asset.domain}</dd></div><div><dt>Source</dt><dd>Curated metadata</dd></div><div><dt>Check execution</dt><dd>Not connected</dd></div></dl></details>
          </>}
          {tab === 'fields' && <><div className="section-line"><div><h2>Attributes</h2><p className="muted">Business meaning and transformation logic, side by side.</p></div><Pill>{asset.columns.length} attributes</Pill></div><div className="table-scroll"><table><thead><tr><th>Attribute / type</th><th>Business definition</th><th>Transformation</th></tr></thead><tbody>{asset.columns.map(c => <tr key={c.name}><td><strong className="mono">{c.name}</strong><small>{c.data_type}</small></td><td>{c.definition || <span className="muted">Not defined</span>}</td><td><code>{c.transformation || 'Not defined'}</code>{c.sources.map((s, i) => <button className="source-link" key={i} onClick={() => {select(s.table); setTab('fields');}}><Link2 size={12}/>{s.table}.{s.column}</button>)}</td></tr>)}</tbody></table></div></>}
          {tab === 'lineage' && <Lineage assets={assets} selected={asset.id} onSelect={select}/>}
          {tab === 'quality' && <QualityPanel key={asset.id} quality={quality}/>}
          {tab === 'impact' && <><div className="section-line"><div><h2>Downstream impact</h2><p className="muted">See which tables and business teams depend on a change.</p></div><label className="impact-filter"><select aria-label="Changed attribute" value={column} onChange={e => setColumn(e.target.value)}><option value="">Any attribute</option>{asset.columns.map(c => <option key={c.name}>{c.name}</option>)}</select></label></div>
            {impactError ? <p className="error" role="alert">{impactError}</p> : !impact ? <p className="muted">Tracing dependencies…</p> : <>
              <div className="impact-summary"><strong>{impact.downstream.length}</strong> downstream tables <span/> <strong>{new Set(impact.contacts.map(c => c.team)).size}</strong> teams to consult</div>
              {!impact.downstream.length ? <div className="empty">No downstream dependencies are recorded for this selection.</div> : <div className="table-scroll"><table><thead><tr><th>Downstream table</th><th>Affected attributes</th><th>Owner</th><th>Dependency</th></tr></thead><tbody>{impact.downstream.map(a => <tr key={a.id}><td><button className="text-button" onClick={() => select(a.id)}>{a.schema_name}.{a.name}</button></td><td>{a.columns.map(c => <code className="inline-code" key={c}>{c}</code>)}</td><td>{a.owner}</td><td><Pill>{a.depth === 1 ? 'Direct' : `${a.depth} steps`}</Pill></td></tr>)}</tbody></table></div>}
              <h3 className="subheading">Teams & points of contact</h3><Contacts people={impact.contacts} onCopy={copyEmail}/><p className="footnote">Derived from recorded attribute lineage and business consumers. Unrecorded dependencies may also exist.</p>
            </>}
          </>}
        </section>
        <footer className="page-footer"><span>Create time: <time dateTime={asset.created_at || undefined}>{formatTime(asset.created_at)}</time></span><span>Update time: <time dateTime={asset.updated_at || undefined}>{formatTime(asset.updated_at)}</time></span></footer>
      </>}
    </main>
    {toast && <div className="toast" role="status">{toast}</div>}
    {modal === 'login' && <Login enabled={session.admin_enabled} onClose={() => setModal('')} onLogin={async () => {setSession(await api('/session')); setModal(''); setToast('Admin editing enabled');}}/>}
    {modal === 'edit' && asset && session.role === 'admin' && <EditAsset asset={asset} assets={assets} onClose={() => setModal('')} onSave={updated => {setAssets(old => old.map(a => a.id === updated.id ? updated : a)); setModal(''); setToast('Metadata saved');}}/>}
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
