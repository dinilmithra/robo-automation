---
hide:
  - navigation
  - toc
---

<div class="ra-target-home">
  <section class="ra-target-hero">
    <div class="ra-target-copy">
      <div class="ra-target-badges">
        <span>◉ Open Source</span>
        <span>Shared Python Automation Infrastructure</span>
      </div>
      <h1>Build Browser<br>Automation.<br><em>Faster. Reliably.</em></h1>
      <p>A reusable Python automation foundation for browser lifecycle, pytest fixtures, logging, diagnostics, configuration, performance monitoring, and parallel test execution.</p>
      <div class="ra-target-actions">
        <a class="ra-target-btn primary" href="getting-started/installation/">🚀&nbsp; Get Started <span>→</span></a>
        <a class="ra-target-btn" href="api/">&lt;/&gt;&nbsp; API Reference <span>→</span></a>
      </div>
      <div class="ra-target-install"><span>pip</span><code>pip install robo-automation</code></div>
    </div>

    <div class="ra-target-art ra-runtime-art" aria-label="robo-automation runtime overview">
      <div class="ra-runtime-brandmark">
        <div class="ra-runtime-emblem" aria-hidden="true"></div>
        <strong class="ra-runtime-wordmark">robo-<em>automation</em></strong>
        <span class="ra-runtime-subtitle">Shared Automation Runtime</span>
      </div>
      <div class="ra-target-float left one"><b>▣</b><span>Browser<br>Lifecycle</span></div>
      <div class="ra-target-float left two"><b>✓</b><span>Pytest<br>Fixtures</span></div>
      <div class="ra-target-float left three"><b>∞</b><span>Parallel<br>Workers</span></div>
      <div class="ra-target-float right one"><b>≡</b><span>Correlated<br>Logging</span></div>
      <div class="ra-target-float right two"><b>◎</b><span>Failure<br>Evidence</span></div>
      <div class="ra-target-float right three"><b>⚡</b><span>Performance<br>Monitoring</span></div>
      <div class="ra-target-float right four"><b>⚙</b><span>Runtime<br>Configuration</span></div>
    </div>
  </section>

  <section class="ra-target-features" aria-label="robo-automation framework capabilities">
    <article><span class="ico">◇</span><div><strong>Reusable Foundation</strong><p>Browser and pytest infrastructure ready for consumer projects.</p></div></article>
    <article><span class="ico">◎</span><div><strong>Stable Wrappers</strong><p>Common page and locator abstractions above browser internals.</p></div></article>
    <article><span class="ico">▤</span><div><strong>Pytest Ready</strong><p>Fixtures, worker lifecycle, and session-level services.</p></div></article>
    <article><span class="ico">ϟ</span><div><strong>Parallel Friendly</strong><p>Designed for isolated xdist workers and credential separation.</p></div></article>
    <article><span class="ico">∞</span><div><strong>Configurable</strong><p>Defaults, environment variables, then fixture overrides.</p></div></article>
    <article><span class="ico">▥</span><div><strong>Clear Diagnostics</strong><p>Logs, screenshots, browser evidence, and performance data.</p></div></article>
  </section>

  <section class="ra-target-workbench">
    <div class="ra-target-code">
      <div class="ra-target-panel-title"><span>›_ &nbsp; Consumer Example</span><span>🐍 Python</span></div>
      <pre><code><span class="ln">1</span> <span class="kw">import</span> pytest
<span class="ln">2</span> <span class="kw">from</span> robo_automation.config <span class="kw">import</span> LoggingConfig
<span class="ln">3</span>
<span class="ln">4</span> <span class="kw">@pytest.fixture</span>(scope=<span class="st">"session"</span>)
<span class="ln">5</span> <span class="kw">def</span> robo_logging_config():
<span class="ln">6</span>     <span class="kw">return</span> LoggingConfig(level=<span class="st">"DEBUG"</span>)
<span class="ln">7</span>
<span class="ln">8</span> <span class="cm"># Fixture override &gt; environment &gt; library default</span></code></pre>
    </div>

    <div class="ra-target-architecture">
      <div class="ra-target-panel-title light"><span>♟ &nbsp; Architecture Overview</span><a href="guides/framework-architecture/">How it works&nbsp; →</a></div>
      <div class="ra-target-arch-flow">
        <div class="node"><span class="node-icon">▤</span><strong>Your Test Project</strong><small>• Business tests<br>• Consumer configuration<br>• Project fixtures</small></div>
        <b>→</b>
        <div class="node library"><div class="library-brand runtime-brand"><span class="runtime-symbol">R</span><span><strong>robo-automation</strong><small>Shared Runtime Layer</small></span></div><ul><li>Browser lifecycle</li><li>Pytest fixtures</li><li>Logging + correlation</li><li>Diagnostics + evidence</li><li>Performance + config</li></ul></div>
        <b>→</b>
        <div class="node"><span class="node-icon">▣</span><strong>Browser Engine</strong><small>• Page<br>• Context<br>• Browser process</small></div>
      </div>
    </div>
  </section>

  <section class="ra-target-docs">
    <div class="ra-target-docs-head"><h2>▣ &nbsp; Documentation</h2><a href="getting-started/installation/">Explore all docs&nbsp; →</a></div>
    <div class="ra-target-doc-grid">
      <a href="getting-started/installation/"><span>↓</span><div><strong>Installation</strong><small>Set up robo-automation.</small></div><b>→</b></a>
      <a href="getting-started/concepts/"><span>⚙</span><div><strong>Core Concepts</strong><small>Understand the shared runtime.</small></div><b>→</b></a>
      <a href="getting-started/pytest-fixtures/"><span>▧</span><div><strong>Pytest Fixtures</strong><small>Use and override public fixtures.</small></div><b>→</b></a>
      <a href="api/"><span>&lt;/&gt;</span><div><strong>API Reference</strong><small>Browse robo-automation APIs.</small></div><b>→</b></a>
      <a href="https://dinilmithra.github.io/robo-appian/api/"><span>A</span><div><strong>robo-appian API</strong><small>Open the published Appian API reference.</small></div><b>↗</b></a>
      <a href="getting-started/error-handling/"><span>!</span><div><strong>Handling Errors</strong><small>Use RoboAutomationError cleanly.</small></div><b>→</b></a>
    </div>
  </section>
</div>
