import React, { useEffect, useState } from 'react';

/**
 * Embeds a teammate's app in a full-height iframe -- but only after
 * confirming their dev server actually answers. If it doesn't (2s
 * timeout), shows a clean "not running" panel with the exact command to
 * start it, instead of letting the browser render its own broken-frame
 * error page inside our app.
 */
export default function TeammateComponentView({ component }) {
  const { name, owner, url, startCommands } = component;
  const [status, setStatus] = useState('checking'); // 'checking' | 'up' | 'down'

  useEffect(() => {
    let cancelled = false;
    setStatus('checking');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    fetch(url, { mode: 'no-cors', cache: 'no-store', signal: controller.signal })
      .then(() => {
        if (!cancelled) setStatus('up');
      })
      .catch(() => {
        if (!cancelled) setStatus('down');
      })
      .finally(() => clearTimeout(timeoutId));

    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [url]);

  return (
    <div className="teammate-view">
      <div className="teammate-view-header">
        <div>
          <h2 className="teammate-view-title">{name}</h2>
          <span className="teammate-view-owner">Owner: {owner}</span>
        </div>
        <a
          className="teammate-view-open-link"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in new tab ↗
        </a>
      </div>

      {status === 'checking' && (
        <div className="teammate-view-checking">
          <div className="spinner" />
          <p>Checking {name}…</p>
        </div>
      )}

      {status === 'down' && (
        <div className="teammate-view-down">
          <h3>{name} is not reachable</h3>
          <p className="teammate-view-owner-line">Owner: {owner}</p>
          <p>This component's server is not running.</p>
          <p className="teammate-view-down-label">Start it with:</p>
          <ul className="teammate-view-commands">
            {startCommands.map((cmd, i) => (
              <li key={i}><code>{cmd}</code></li>
            ))}
          </ul>
        </div>
      )}

      {status === 'up' && (
        <iframe
          className="teammate-iframe"
          src={url}
          title={`${name} (${owner})`}
        />
      )}
    </div>
  );
}
